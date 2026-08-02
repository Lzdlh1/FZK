"""AI 学习(schema):对话式训练样本的请求/响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.parse_job import FieldResult


class LearnTryResponse(BaseModel):
    """一次「上传示例图纸 → AI 尝试解析」的结果。"""

    image_oid: str
    drawing_name: str
    fields: dict[str, FieldResult] = Field(default_factory=dict)
    meta: dict = Field(default_factory=dict)
    message: str | None = None


class LearnSampleCreate(BaseModel):
    """保存一条训练样本。"""

    template_id: UUID
    image_oid: str
    expected_json: dict[str, Any]


class LearnSampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID
    image_oid: str
    expected_json: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0
    created_at: datetime
