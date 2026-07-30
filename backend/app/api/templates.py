"""模板 CRUD API:模板/变量/映射的增删改查与 DAG 校验。

子路由路径不含 /api 前缀,由 api/__init__.py 统一挂载到 /api 下。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.template import Template
from app.models.user import User
from app.models.variable import Mapping, Variable
from app.schemas.common import DagValidateResult
from app.schemas.mapping import MappingCreate, MappingOut
from app.schemas.template import (
    TemplateCreate,
    TemplateListItem,
    TemplateOut,
    TemplateUpdate,
    VariableOut,
)
from app.schemas.variable import VariableCreate
from app.services.template_loader import (
    load_variables_with_relations,
    template_to_out,
    validate_template_dag,
    variable_to_out,
)

router = APIRouter()


def _get_template_or_404(
    db: Session, template_id: uuid.UUID, owner_id: uuid.UUID | None = None
) -> Template:
    template = db.query(Template).filter(Template.id == template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    if owner_id is not None and template.owner_id != owner_id:
        # 不泄漏存在性,统一返回 404
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


# ---------------------------------------------------------------------------
# 模板
# ---------------------------------------------------------------------------
@router.get("/templates", response_model=list[TemplateListItem])
def list_templates(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    templates = (
        db.query(Template)
        .filter(Template.owner_id == user.id)
        .order_by(Template.updated_at.desc())
        .all()
    )
    return templates


@router.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = Template(
        name=payload.name,
        owner_id=user.id,
        univer_snapshot=payload.univer_snapshot,
        version=1,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template_to_out(db, template, include_variables=False)


@router.get("/templates/{template_id}", response_model=TemplateOut)
def get_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = _get_template_or_404(db, template_id, owner_id=user.id)
    return template_to_out(db, template, include_variables=True)


@router.put("/templates/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: uuid.UUID,
    payload: TemplateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = _get_template_or_404(db, template_id, owner_id=user.id)
    if payload.name is not None:
        template.name = payload.name
    if payload.univer_snapshot is not None:
        template.univer_snapshot = payload.univer_snapshot
    db.commit()
    db.refresh(template)
    return template_to_out(db, template, include_variables=True)


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = _get_template_or_404(db, template_id, owner_id=user.id)
    db.delete(template)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 模板下的变量
# ---------------------------------------------------------------------------
@router.get("/templates/{template_id}/variables", response_model=list[VariableOut])
def list_variables(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = _get_template_or_404(db, template_id, owner_id=user.id)
    return [variable_to_out(v) for v in load_variables_with_relations(db, template.id)]


@router.post(
    "/templates/{template_id}/variables",
    response_model=VariableOut,
    status_code=status.HTTP_201_CREATED,
)
def create_variable(
    template_id: uuid.UUID,
    payload: VariableCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = _get_template_or_404(db, template_id, owner_id=user.id)
    variable = Variable(
        template_id=template.id,
        name=payload.name,
        placeholder=payload.placeholder,
        sheet=payload.sheet,
        cell=payload.cell,
        source_type=payload.source_type,
        data_type=payload.data_type,
        unit=payload.unit,
        enabled=payload.enabled,
        depends_on=list(payload.depends_on or []),
    )
    db.add(variable)
    db.flush()
    result = validate_template_dag(db, template.id)
    if not result["valid"]:
        db.rollback()
        raise HTTPException(status_code=400, detail=result)
    db.commit()
    db.refresh(variable)
    return variable_to_out(variable)


# ---------------------------------------------------------------------------
# 模板下的映射
# ---------------------------------------------------------------------------
@router.get("/templates/{template_id}/mappings", response_model=list[MappingOut])
def list_mappings(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = _get_template_or_404(db, template_id, owner_id=user.id)
    return (
        db.query(Mapping)
        .filter(Mapping.template_id == template.id)
        .order_by(Mapping.drawing_field.asc())
        .all()
    )


@router.post(
    "/templates/{template_id}/mappings",
    response_model=MappingOut,
    status_code=status.HTTP_201_CREATED,
)
def create_mapping(
    template_id: uuid.UUID,
    payload: MappingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = _get_template_or_404(db, template_id, owner_id=user.id)
    mapping = Mapping(
        template_id=template.id,
        drawing_field=payload.drawing_field,
        variable_id=payload.variable_id,
        auto_matched=payload.auto_matched,
        confirmed=payload.confirmed,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


# ---------------------------------------------------------------------------
# DAG 校验
# ---------------------------------------------------------------------------
@router.post("/templates/{template_id}/validate-dag", response_model=DagValidateResult)
def validate_dag_endpoint(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = _get_template_or_404(db, template_id, owner_id=user.id)
    return validate_template_dag(db, template.id)
