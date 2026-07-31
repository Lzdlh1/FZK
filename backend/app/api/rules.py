"""规则 API：教 AI 如何处理图纸数据和图示的规则 CRUD。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.rule import Rule as RuleModel
from app.models.user import User
from app.schemas.rule import RuleCreate, RuleOut, RuleUpdate

router = APIRouter()


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作规则")


@router.get("/rules", response_model=list[RuleOut])
def list_rules(
    category: str | None = None,
    enabled: bool | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(RuleModel)
    if category:
        q = q.filter(RuleModel.category == category)
    if enabled is not None:
        q = q.filter(RuleModel.enabled == enabled)
    return q.order_by(RuleModel.sort_order, RuleModel.created_at).all()


@router.post("/rules", response_model=RuleOut)
def create_rule(
    body: RuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    row = RuleModel(
        name=body.name,
        content=body.content,
        category=body.category,
        scope=body.scope,
        enabled=body.enabled,
        sort_order=body.sort_order,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/rules/{rule_id}", response_model=RuleOut)
def update_rule(
    rule_id: UUID,
    body: RuleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    row = db.query(RuleModel).filter(RuleModel.id == rule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="规则不存在")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    row = db.query(RuleModel).filter(RuleModel.id == rule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}
