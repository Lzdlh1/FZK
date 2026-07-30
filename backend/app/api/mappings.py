"""映射 CRUD API:更新/删除映射。

子路由路径不含 /api 前缀,由 api/__init__.py 统一挂载到 /api 下。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.variable import Mapping
from app.schemas.mapping import MappingOut, MappingUpdate

router = APIRouter()


@router.put("/mappings/{mid}", response_model=MappingOut)
def update_mapping(
    mid: uuid.UUID,
    payload: MappingUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    mapping = db.query(Mapping).filter(Mapping.id == mid).first()
    if mapping is None:
        raise HTTPException(status_code=404, detail="映射不存在")
    if payload.drawing_field is not None:
        mapping.drawing_field = payload.drawing_field
    if payload.variable_id is not None:
        mapping.variable_id = payload.variable_id
    if payload.auto_matched is not None:
        mapping.auto_matched = payload.auto_matched
    if payload.confirmed is not None:
        mapping.confirmed = payload.confirmed
    db.commit()
    db.refresh(mapping)
    return mapping


@router.delete("/mappings/{mid}")
def delete_mapping(
    mid: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    mapping = db.query(Mapping).filter(Mapping.id == mid).first()
    if mapping is None:
        raise HTTPException(status_code=404, detail="映射不存在")
    db.delete(mapping)
    db.commit()
    return {"ok": True}
