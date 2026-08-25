from fastapi import APIRouter

from emc_backend.api.v1.health import router as health_router
from emc_backend.api.v1.models import router as models_router
from emc_backend.api.v1.sessions import router as sessions_router
from emc_backend.api.v1.workspaces import router as workspaces_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(models_router)
api_router.include_router(sessions_router)
api_router.include_router(workspaces_router)
