import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.metric_alert import MetricAlert
from app.models.metric_snapshot import MetricSnapshot
from app.schemas.metrics import MetricAlertRead, MetricSnapshotRead
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/", response_model=list[MetricSnapshotRead])
async def list_metrics(
    source: str | None = None,
    metric_name: str | None = None,
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = select(MetricSnapshot).where(MetricSnapshot.recorded_at >= since)
    if source:
        query = query.where(MetricSnapshot.source == source)
    if metric_name:
        query = query.where(MetricSnapshot.metric_name == metric_name)
    query = query.order_by(MetricSnapshot.recorded_at.desc()).limit(500)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/alerts", response_model=list[MetricAlertRead])
async def list_alerts(
    severity: str | None = None,
    resolved: bool | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = select(MetricAlert).order_by(MetricAlert.created_at.desc()).limit(100)
    if severity:
        query = query.where(MetricAlert.severity == severity)
    if resolved is not None:
        query = query.where(MetricAlert.is_resolved == resolved)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/revenue-formula")
async def get_revenue_formula(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    analytics = AnalyticsService()
    tenant_id = uuid.UUID(current_user["tenant_id"])
    return await analytics.get_revenue_formula(session, tenant_id)


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await session.execute(select(MetricAlert).where(MetricAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert:
        alert.is_resolved = True
        await session.commit()
    return {"status": "resolved"}
