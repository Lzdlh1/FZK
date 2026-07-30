from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TemplateCreate(BaseModel):
    name: str
    univer_snapshot: dict[str, Any]


class TemplateUpdate(BaseModel):
    name: str | None = None
    univer_snapshot: dict[str, Any] | None = None


class VariablePromptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    prompt: str
    output_constraints: dict[str, Any] | None = None
    confidence_threshold: float = 0.7
    post_process: dict[str, Any] | None = None


class FormulaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    kind: str
    expression: str
    preset_rule_id: UUID | None = None
    dependencies: list[UUID] = Field(default_factory=list)


class VariableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    placeholder: str
    sheet: str
    cell: str
    source_type: str
    data_type: str
    unit: str | None = None
    enabled: bool = True
    depends_on: list[UUID] = Field(default_factory=list)
    prompt: VariablePromptOut | None = None
    formula: FormulaOut | None = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    version: int = 1
    updated_at: datetime | None = None
    owner_id: UUID | None = None
    variables: list[VariableOut] = Field(default_factory=list)


class TemplateListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    version: int = 1
    updated_at: datetime | None = None
