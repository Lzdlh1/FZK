"""变量 CRUD API:更新/删除变量,prompt/formula upsert。

子路由路径不含 /api 前缀,由 api/__init__.py 统一挂载到 /api 下。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.formula import Formula
from app.models.user import User
from app.models.variable import Variable, VariablePrompt
from app.schemas.template import FormulaOut, VariableOut, VariablePromptOut
from app.schemas.variable import FormulaUpsert, VariablePromptUpsert, VariableUpdate
from app.services.formula.engine import extract_var_refs
from app.services.template_loader import validate_template_dag, variable_to_out

router = APIRouter()


def _get_variable_or_404(db: Session, vid: uuid.UUID) -> Variable:
    variable = db.query(Variable).filter(Variable.id == vid).first()
    if variable is None:
        raise HTTPException(status_code=404, detail="变量不存在")
    return variable


@router.put("/variables/{vid}", response_model=VariableOut)
def update_variable(
    vid: uuid.UUID,
    payload: VariableUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    variable = _get_variable_or_404(db, vid)
    structure_changed = False
    if payload.name is not None and payload.name != variable.name:
        variable.name = payload.name
        structure_changed = True
    if payload.placeholder is not None:
        variable.placeholder = payload.placeholder
    if payload.sheet is not None:
        variable.sheet = payload.sheet
    if payload.cell is not None:
        variable.cell = payload.cell
    if payload.source_type is not None and payload.source_type != variable.source_type:
        variable.source_type = payload.source_type
        structure_changed = True
    if payload.data_type is not None:
        variable.data_type = payload.data_type
    if payload.unit is not None:
        variable.unit = payload.unit
    if payload.enabled is not None:
        variable.enabled = payload.enabled
    if payload.depends_on is not None:
        variable.depends_on = list(payload.depends_on)
        structure_changed = True

    db.flush()
    if structure_changed:
        result = validate_template_dag(db, variable.template_id)
        if not result["valid"]:
            db.rollback()
            raise HTTPException(status_code=400, detail=result)
    db.commit()
    db.refresh(variable)
    return variable_to_out(variable)


@router.delete("/variables/{vid}")
def delete_variable(
    vid: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    variable = _get_variable_or_404(db, vid)
    template_id = variable.template_id
    # 清理同模板其它变量 depends_on 中对本 id 的引用(数组内 UUID,非 FK,需手动移除)
    siblings = (
        db.query(Variable)
        .filter(Variable.template_id == template_id, Variable.id != vid)
        .all()
    )
    for s in siblings:
        if vid in (s.depends_on or []):
            s.depends_on = [d for d in s.depends_on if d != vid]
    db.delete(variable)
    db.commit()
    return {"ok": True}


@router.put("/variables/{vid}/prompt", response_model=VariablePromptOut)
def upsert_prompt(
    vid: uuid.UUID,
    payload: VariablePromptUpsert,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    variable = _get_variable_or_404(db, vid)
    if variable.source_type != "extract":
        raise HTTPException(status_code=400, detail="仅 extract 型变量支持配置 prompt")
    prompt = db.query(VariablePrompt).filter(VariablePrompt.variable_id == vid).first()
    if prompt is None:
        prompt = VariablePrompt(
            variable_id=vid,
            prompt=payload.prompt,
            output_constraints=payload.output_constraints or {},
            confidence_threshold=payload.confidence_threshold,
            post_process=payload.post_process or {},
        )
        db.add(prompt)
    else:
        prompt.prompt = payload.prompt
        prompt.output_constraints = payload.output_constraints or {}
        prompt.confidence_threshold = payload.confidence_threshold
        prompt.post_process = payload.post_process or {}
    db.commit()
    db.refresh(prompt)
    return prompt


@router.put("/variables/{vid}/formula", response_model=FormulaOut)
def upsert_formula(
    vid: uuid.UUID,
    payload: FormulaUpsert,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    variable = _get_variable_or_404(db, vid)
    if variable.source_type != "formula":
        raise HTTPException(status_code=400, detail="仅 formula 型变量支持配置公式")

    # 从表达式派生依赖变量名 -> 同模板内变量 id
    names = extract_var_refs(payload.expression)
    deps: list[uuid.UUID] = []
    if names:
        refs = (
            db.query(Variable)
            .filter(
                Variable.template_id == variable.template_id,
                Variable.name.in_(names),
            )
            .all()
        )
        name_to_id = {r.name: r.id for r in refs}
        for n in names:
            if n not in name_to_id:
                raise HTTPException(
                    status_code=400, detail=f"公式引用了不存在的变量: {n}"
                )
            deps.append(name_to_id[n])

    formula = db.query(Formula).filter(Formula.variable_id == vid).first()
    if formula is None:
        formula = Formula(
            variable_id=vid,
            kind=payload.kind,
            expression=payload.expression,
            preset_rule_id=payload.preset_rule_id,
            dependencies=deps,
        )
        db.add(formula)
    else:
        formula.kind = payload.kind
        formula.expression = payload.expression
        formula.preset_rule_id = payload.preset_rule_id
        formula.dependencies = deps

    variable.depends_on = deps
    db.flush()
    result = validate_template_dag(db, variable.template_id)
    if not result["valid"]:
        db.rollback()
        raise HTTPException(status_code=400, detail=result)
    db.commit()
    db.refresh(formula)
    return formula
