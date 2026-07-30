"""公式求值 API。

子路由路径不含 /api 前缀,由 api/__init__.py 统一挂载到 /api 下。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import FormulaEvaluateRequest, FormulaEvaluateResponse
from app.services.formula.engine import FormulaError, evaluate

router = APIRouter()


@router.post("/formula/evaluate", response_model=FormulaEvaluateResponse)
def evaluate_formula(
    payload: FormulaEvaluateRequest,
    _user: User = Depends(get_current_user),
):
    try:
        result = evaluate(payload.expression, payload.values)
    except FormulaError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return FormulaEvaluateResponse(
        value=result["value"],
        substituted_expression=result["substituted_expression"],
        db_refs=result["db_refs"],
    )
