"""规则 schema：教 AI 如何处理图纸数据和图示。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RuleCreate(BaseModel):
    name: str
    content: str
    category: str = "通用"
    scope: str | None = None
    enabled: bool = True
    sort_order: int = 0


class RuleUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    category: str | None = None
    scope: str | None = None
    enabled: bool | None = None
    sort_order: int | None = None


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    content: str
    category: str
    scope: str | None
    enabled: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
