from fastapi import APIRouter

from app.api.v1.employees import router as employees_router
from app.api.v1.health import router as health_router
from app.api.v1.meetings import router as meetings_router
from app.api.v1.tasks import router as tasks_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health_router)
v1_router.include_router(employees_router)
v1_router.include_router(meetings_router)
v1_router.include_router(tasks_router)
