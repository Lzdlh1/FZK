from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DagValidateResult(BaseModel):
    valid: bool
    cycles: list[list[str]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class FormulaEvaluateRequest(BaseModel):
    expression: str
    values: dict[str, float] = Field(default_factory=dict)


class FormulaEvaluateResponse(BaseModel):
    value: float
    substituted_expression: str
    db_refs: list[Any] = Field(default_factory=list)
