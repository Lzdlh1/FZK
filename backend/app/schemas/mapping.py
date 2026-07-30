from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MappingCreate(BaseModel):
    drawing_field: str
    variable_id: UUID
    auto_matched: bool = False
    confirmed: bool = False


class MappingUpdate(BaseModel):
    drawing_field: str | None = None
    variable_id: UUID | None = None
    auto_matched: bool | None = None
    confirmed: bool | None = None


class MappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    template_id: UUID
    drawing_field: str
    variable_id: UUID
    auto_matched: bool = False
    confirmed: bool = False
