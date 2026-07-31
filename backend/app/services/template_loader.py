"""模板/变量序列化加载器:批量装载 variables 及其 prompt/formula,避免 N+1。

供 templates / parse_jobs 等 API 复用。
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.formula import Formula
from app.models.template import Template
from app.models.variable import Variable, VariablePrompt
from app.schemas.template import FormulaOut, TemplateOut, VariableOut, VariablePromptOut
from app.services.dag import validate_dag


def load_variables_with_relations(db: Session, template_id: uuid.UUID) -> list[Variable]:
    """加载模板下全部变量(按 name 排序),并一次性挂载 prompt/formula。"""
    variables = (
        db.query(Variable)
        .filter(Variable.template_id == template_id)
        .order_by(Variable.name.asc())
        .all()
    )
    if not variables:
        return []
    var_ids = [v.id for v in variables]
    prompt_map = {
        p.variable_id: p
        for p in db.query(VariablePrompt)
        .filter(VariablePrompt.variable_id.in_(var_ids))
        .all()
    }
    formula_map = {
        f.variable_id: f
        for f in db.query(Formula).filter(Formula.variable_id.in_(var_ids)).all()
    }
    for v in variables:
        v.prompt = prompt_map.get(v.id)
        v.formula = formula_map.get(v.id)
    return variables


def variable_to_out(v: Variable) -> VariableOut:
    """将 ORM 变量转为 VariableOut,读取已挂载的 prompt/formula(未挂载则视为无)。"""
    prompt = None
    p = getattr(v, "prompt", None)
    if p is not None:
        prompt = VariablePromptOut.model_validate(p)
    formula = None
    f = getattr(v, "formula", None)
    if f is not None:
        formula = FormulaOut.model_validate(f)
    return VariableOut(
        id=v.id,
        name=v.name,
        placeholder=v.placeholder,
        sheet=v.sheet,
        cell=v.cell,
        source_type=v.source_type,
        data_type=v.data_type,
        unit=v.unit,
        enabled=v.enabled,
        depends_on=list(v.depends_on or []),
        prompt=prompt,
        formula=formula,
    )


def template_to_out(
    db: Session, template: Template, include_variables: bool = True
) -> TemplateOut:
    """构造 TemplateOut;include_variables 时批量加载变量(含 prompt/formula)。"""
    variables: list[VariableOut] = []
    if include_variables:
        variables = [variable_to_out(v) for v in load_variables_with_relations(db, template.id)]
    return TemplateOut(
        id=template.id,
        name=template.name,
        version=template.version,
        updated_at=template.updated_at,
        owner_id=template.owner_id,
        univer_snapshot=template.univer_snapshot,
        variables=variables,
    )


def validate_template_dag(db: Session, template_id: uuid.UUID) -> dict:
    """加载模板全部变量并做 DAG 校验,返回 {valid, cycles, errors}。"""
    variables = db.query(Variable).filter(Variable.template_id == template_id).all()
    return validate_dag(variables)
