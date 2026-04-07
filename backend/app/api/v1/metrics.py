"""Метрики из внешних систем (DentalPro, 1C, Bitrix24), алерты и формула выручки.

Модуль предоставляет доступ к бизнес-метрикам клиники:
- Просмотр снимков метрик (снэпшотов) с фильтрацией по источнику и имени;
- Просмотр и разрешение алертов при отклонениях метрик от нормы;
- Расчёт формулы выручки: кресла * загрузка * средний чек.

Данные собираются автоматически воркером ``collect_metrics`` и сохраняются
в таблицу ``metric_snapshots``. Алерты генерируются при критических
отклонениях и отправляются CEO в Telegram.
"""

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
    """Возвращает снимки метрик за указанный период.

    Позволяет фильтровать по источнику (``dental_pro``, ``1c``, ``bitrix24``)
    и имени метрики (``revenue_monthly``, ``utilization_percent`` и т.д.).
    Ограничение — 500 записей, отсортированных от новых к старым.
    Используется для построения графиков на дашборде CEO.

    Args:
        source: Фильтр по системе-источнику метрики.
        metric_name: Фильтр по названию метрики.
        days: Глубина выборки в днях (1-365, по умолчанию 30).
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        list[MetricSnapshotRead]: Снимки метрик за период.
    """
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
    """Возвращает список алертов по метрикам.

    Алерты генерируются автоматически при отклонении метрик от пороговых
    значений. Поддерживает фильтрацию по серьёзности (``critical``,
    ``warning``, ``info``) и статусу разрешения. Максимум 100 записей.

    Args:
        severity: Фильтр по уровню серьёзности.
        resolved: Фильтр по статусу: ``True`` — разрешённые, ``False`` — активные.
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        list[MetricAlertRead]: Список алертов.
    """
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
    """Рассчитывает формулу выручки клиники.

    Формула: ``выручка = кресла * загрузка (%) * средний чек``.
    Сравнивает фактическую выручку с целевой и показывает разрыв
    в процентах. Используется CEO для понимания, какой параметр
    формулы «проседает» и требует управленческого вмешательства.

    Args:
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        RevenueFormulaRead: Компоненты формулы, факт, план и разрыв.
    """
    analytics = AnalyticsService()
    tenant_id = uuid.UUID(current_user["tenant_id"])
    return await analytics.get_revenue_formula(session, tenant_id)


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Отмечает алерт как разрешённый.

    CEO помечает алерт после того, как принял меры по устранению
    проблемы. Разрешённые алерты не отображаются в активных уведомлениях.

    Args:
        alert_id: UUID алерта для разрешения.
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        dict: ``{"status": "resolved"}``.
    """
    result = await session.execute(select(MetricAlert).where(MetricAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert:
        alert.is_resolved = True
        await session.commit()
    return {"status": "resolved"}
