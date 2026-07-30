from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PresetRuleCreate(BaseModel):
    name: str
    category: str | None = None
    expression_template: str
    params: dict[str, Any] = Field(default_factory=dict)
    output_unit: str | None = None
    enabled: bool = True


class PresetRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    category: str | None = None
    expression_template: str
    params: dict[str, Any] = Field(default_factory=dict)
    output_unit: str | None = None
    enabled: bool = True
    version: int = 1
    built_in: bool = False
