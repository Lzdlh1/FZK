"""设置 API：AI 供应商 CRUD + 健康检查，数据库参数 CRUD。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.ai_provider import AIProvider as AIProviderModel
from app.models.database_param import DatabaseParam as DatabaseParamModel
from app.models.user import User
from app.schemas.settings import (
    AIProviderCreate,
    AIProviderHealthResult,
    AIProviderOut,
    AIProviderUpdate,
    DatabaseParamCreate,
    DatabaseParamOut,
    DatabaseParamUpdate,
)

router = APIRouter()


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作设置")


# ===================== AI 供应商 =====================

@router.get("/ai-providers", response_model=list[AIProviderOut])
def list_ai_providers(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return db.query(AIProviderModel).order_by(AIProviderModel.weight.desc()).all()


@router.post("/ai-providers", response_model=AIProviderOut)
def create_ai_provider(
    body: AIProviderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    row = AIProviderModel(
        name=body.name,
        endpoint=body.endpoint,
        api_key_enc=body.api_key,
        model=body.model,
        weight=body.weight,
        healthy=body.healthy,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/ai-providers/{provider_id}", response_model=AIProviderOut)
def update_ai_provider(
    provider_id: UUID,
    body: AIProviderUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    row = db.query(AIProviderModel).filter(AIProviderModel.id == provider_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="AI 供应商不存在")
    data = body.model_dump(exclude_unset=True)
    if "api_key" in data:
        row.api_key_enc = data.pop("api_key")
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/ai-providers/{provider_id}")
def delete_ai_provider(
    provider_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    row = db.query(AIProviderModel).filter(AIProviderModel.id == provider_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="AI 供应商不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/ai-providers/{provider_id}/health", response_model=AIProviderHealthResult)
async def check_ai_provider_health(
    provider_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    row = db.query(AIProviderModel).filter(AIProviderModel.id == provider_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="AI 供应商不存在")

    from app.ai.providers.openai_compatible import OpenAICompatibleProvider

    provider = OpenAICompatibleProvider(
        name=row.name,
        endpoint=row.endpoint,
        api_key=row.api_key_enc,
        model=row.model,
        weight=row.weight,
    )
    error = None
    try:
        ok = await provider.health()
    except Exception as exc:
        ok = False
        error = str(exc)
    row.healthy = ok
    if ok:
        from datetime import datetime, timezone
        row.last_check_at = datetime.now(timezone.utc)
    db.commit()
    return AIProviderHealthResult(id=row.id, name=row.name, healthy=ok, error=error)


# ===================== 数据库参数 =====================

@router.get("/database-params", response_model=list[DatabaseParamOut])
def list_database_params(
    category: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(DatabaseParamModel)
    if category:
        q = q.filter(DatabaseParamModel.category == category)
    return q.order_by(DatabaseParamModel.category, DatabaseParamModel.model).all()


@router.post("/database-params", response_model=DatabaseParamOut)
def create_database_param(
    body: DatabaseParamCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    row = DatabaseParamModel(
        category=body.category,
        model=body.model,
        field=body.field,
        value=body.value,
        unit=body.unit,
        enabled=body.enabled,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/database-params/{param_id}", response_model=DatabaseParamOut)
def update_database_param(
    param_id: UUID,
    body: DatabaseParamUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    row = db.query(DatabaseParamModel).filter(DatabaseParamModel.id == param_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="数据库参数不存在")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/database-params/{param_id}")
def delete_database_param(
    param_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(user)
    row = db.query(DatabaseParamModel).filter(DatabaseParamModel.id == param_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="数据库参数不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}
