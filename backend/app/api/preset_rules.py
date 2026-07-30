"""预设规则 API:列表与创建(创建仅 admin)。

本 router 由 api/__init__.py 以 prefix="/preset-rules" 挂载,
内部路径为空串,最终路由为 /api/preset-rules。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.preset_rule import PresetRule
from app.models.user import User
from app.schemas.preset_rule import PresetRuleCreate, PresetRuleOut

router = APIRouter()


@router.get("", response_model=list[PresetRuleOut])
def list_preset_rules(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return db.query(PresetRule).order_by(PresetRule.name.asc()).all()


@router.post("", response_model=PresetRuleOut, status_code=status.HTTP_201_CREATED)
def create_preset_rule(
    payload: PresetRuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可创建预设规则")
    rule = PresetRule(
        name=payload.name,
        category=payload.category,
        expression_template=payload.expression_template,
        params=payload.params,
        output_unit=payload.output_unit,
        enabled=payload.enabled,
        built_in=False,
        version=1,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
