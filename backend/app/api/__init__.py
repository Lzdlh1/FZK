from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.formula import router as formula_router
from app.api.mappings import router as mappings_router
from app.api.parse_jobs import router as parse_jobs_router
from app.api.preset_rules import router as preset_rules_router
from app.api.rules import router as rules_router
from app.api.settings import router as settings_router
from app.api.templates import router as templates_router
from app.api.variables import router as variables_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(templates_router, tags=["templates"])
api_router.include_router(variables_router, tags=["variables"])
api_router.include_router(mappings_router, tags=["mappings"])
api_router.include_router(formula_router, tags=["formula"])
api_router.include_router(preset_rules_router, prefix="/preset-rules", tags=["preset-rules"])
api_router.include_router(parse_jobs_router, tags=["parse-jobs"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(rules_router, tags=["rules"])
