from fastapi import APIRouter

from app.api.v1.calendar import router as calendar_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.employees import router as employees_router
from app.api.v1.health import router as health_router
from app.api.v1.meetings import router as meetings_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.peer_reviews import router as peer_reviews_router
from app.api.v1.reports import router as reports_router
from app.api.v1.scores import router as scores_router
from app.api.v1.tasks import router as tasks_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(employees_router)
v1_router.include_router(meetings_router)
v1_router.include_router(tasks_router)
v1_router.include_router(reports_router)
v1_router.include_router(calendar_router)
v1_router.include_router(metrics_router)
v1_router.include_router(scores_router)
v1_router.include_router(peer_reviews_router)
