from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.template import TemplateOut


class FieldResult(BaseModel):
    value: Any = None
    confidence: float | None = None
    source_region: dict | None = None
    raw_text: str | None = None
    unit: str | None = None
    alternatives: list[Any] = Field(default_factory=list)
    status: str = "ok"
    substituted_expression: str | None = None
    db_refs: list[Any] | None = None
    error: str | None = None
    highlight: bool | None = None


class ParseJobResult(BaseModel):
    fields: dict[str, FieldResult] = Field(default_factory=dict)
    meta: dict = Field(default_factory=dict)
    error: str | None = None
    template_snapshot_ref: dict | None = None
    db_version: dict | None = None
    rule_version: dict | None = None
    completed_at: str | None = None


class ParseJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID
    drawing_name: str
    status: str
    result: ParseJobResult | None = None
    created_at: datetime
    template: TemplateOut | None = None


class ParseJobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID
    drawing_name: str
    status: str
    created_at: datetime


class ReviewRequest(BaseModel):
    edits: dict[str, Any] = Field(default_factory=dict)
    manual_overrides: list[str] = Field(default_factory=list)


class RerunFieldRequest(BaseModel):
    variable_id: str


class OutputRequest(BaseModel):
    filename: str | None = None


class OutputResponse(BaseModel):
    output_url: str
    snapshot_id: str
    filename: str


class HistorySnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parse_job_id: UUID
    drawing_oid: str
    template_snapshot: dict = Field(default_factory=dict)
    db_version: dict = Field(default_factory=dict)
    rule_version: dict = Field(default_factory=dict)
    ai_raw_result: dict = Field(default_factory=dict)
    manual_edits: dict = Field(default_factory=dict)
    output_oid: str | None = None
    created_at: datetime
