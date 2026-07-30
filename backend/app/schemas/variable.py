from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.template import FormulaOut, VariablePromptOut


class VariableCreate(BaseModel):
    name: str
    placeholder: str
    sheet: str
    cell: str
    source_type: str  # extract|database|formula|manual
    data_type: str    # string|number|integer|enum
    unit: str | None = None
    enabled: bool = True
    depends_on: list[UUID] = Field(default_factory=list)


class VariableUpdate(BaseModel):
    name: str | None = None
    placeholder: str | None = None
    sheet: str | None = None
    cell: str | None = None
    source_type: str | None = None
    data_type: str | None = None
    unit: str | None = None
    enabled: bool | None = None
    depends_on: list[UUID] | None = None


class VariablePromptUpsert(BaseModel):
    prompt: str
    output_constraints: dict[str, Any] | None = None
    confidence_threshold: float = 0.7
    post_process: dict[str, Any] | None = None


class FormulaUpsert(BaseModel):
    kind: str  # preset|custom
    expression: str
    preset_rule_id: UUID | None = None
