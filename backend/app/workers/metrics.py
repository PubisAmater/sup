"""Сбор метрик из внешних систем (DentalPro, 1C, Bitrix24) и проверка алертов.

Модуль содержит два arq-воркера для автоматического мониторинга бизнес-показателей:

- ``collect_metrics`` — периодически опрашивает внешние системы (DentalPro, 1C, Bitrix24),
  собирает ключевые метрики (загрузка кресел, выручка, маржа, лиды, конверсия и т.д.)
  и сохраняет снимки в таблицу ``metric_snapshots``;
- ``check_metric_alerts`` — анализирует собранные метрики на предмет отклонений
  от пороговых значений и отправляет критические/warning алерты CEO в Telegram.

Зачем: CEO видит актуальные бизнес-метрики на дашборде и получает мгновенные
уведомления при проблемах, не дожидаясь еженедельных отчётов.
"""

import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.config import get_settings

logger = logging.getLogger(__name__)


async def collect_metrics(ctx: dict) -> None:
    """Собирает бизнес-метрики из внешних систем для всех активных тенантов.

    Для каждого активного тенанта последовательно опрашивает три системы:

    - **DentalPro**: количество кресел, загрузка (%), средний чек;
    - **1C**: месячная выручка, маржа (%), ФОТ;
    - **Bitrix24**: количество лидов, конверсия, сумма сделок.

    Каждая метрика сохраняется как ``MetricSnapshot`` с указанием источника,
    имени метрики, значения и времени записи. Ошибки отдельных систем
    не блокируют сбор из остальных (graceful degradation).

    Зачем: формирует историческую базу метрик для графиков на дашборде
    и для формулы выручки (кресла * загрузка * средний чек).

    Args:
        ctx: Контекст arq-воркера.
    """
    from app.database import async_session_factory
    from app.models.metric_snapshot import MetricSnapshot
    from app.models.tenant import Tenant
    from app.services.bitrix24 import Bitrix24Service
    from app.services.dental_pro import DentalProService
    from app.services.onec import OneCService

    now = datetime.now(timezone.utc)
    today = date.today()
    month_start = today.replace(day=1)

    async with async_session_factory() as session:
        tenants_result = await session.execute(
            select(Tenant).where(Tenant.is_active.is_(True))
        )
        tenants = tenants_result.scalars().all()

        for tenant in tenants:
            snapshots = []

            # Dental Pro metrics
            try:
                dental = DentalProService()
                chairs = await dental.get_chairs_count()
                utilization = await dental.get_utilization(month_start, today)
                avg_check = await dental.get_avg_check(month_start, today)

                for name, value in [
                    ("chairs_count", chairs),
                    ("utilization_percent", utilization),
                    ("avg_check", avg_check),
                ]:
                    snapshots.append(MetricSnapshot(
                        id=uuid.uuid4(), tenant_id=tenant.id,
                        source="dental_pro", metric_name=name,
                        metric_value=float(value), recorded_at=now,
                    ))
            except Exception as e:
                logger.error("DentalPro metrics collection failed: %s", e)

            # 1C metrics
            try:
                onec = OneCService()
                revenue = await onec.get_revenue(month_start, today)
                margin = await onec.get_margin(month_start, today)
                payroll = await onec.get_payroll(month_start, today)

                for name, value in [
                    ("revenue_monthly", revenue),
                    ("margin_percent", margin),
                    ("payroll_monthly", payroll),
                ]:
                    snapshots.append(MetricSnapshot(
                        id=uuid.uuid4(), tenant_id=tenant.id,
                        source="1c", metric_name=name,
                        metric_value=float(value), recorded_at=now,
                    ))
            except Exception as e:
                logger.error("1C metrics collection failed: %s", e)

            # Bitrix24 metrics
            try:
                bitrix = Bitrix24Service()
                leads = await bitrix.get_leads_count()
                deals = await bitrix.get_deals_stats()

                snapshots.append(MetricSnapshot(
                    id=uuid.uuid4(), tenant_id=tenant.id,
                    source="bitrix24", metric_name="leads_count",
                    metric_value=float(leads), recorded_at=now,
                ))
                snapshots.append(MetricSnapshot(
                    id=uuid.uuid4(), tenant_id=tenant.id,
                    source="bitrix24", metric_name="lead_conversion",
                    metric_value=deals["conversion_rate"], recorded_at=now,
                ))
                snapshots.append(MetricSnapshot(
                    id=uuid.uuid4(), tenant_id=tenant.id,
                    source="bitrix24", metric_name="deals_amount",
                    metric_value=deals["total_amount"], recorded_at=now,
                ))
            except Exception as e:
                logger.error("Bitrix24 metrics collection failed: %s", e)

            for s in snapshots:
                session.add(s)
            await session.commit()
            logger.info("Collected %d metrics for tenant %s", len(snapshots), tenant.slug)


async def check_metric_alerts(ctx: dict) -> None:
    """Проверяет метрики на отклонения от пороговых значений и генерирует алерты.

    Для каждого активного тенанта вызывает ``AnalyticsService.check_deviations``,
    который сравнивает текущие метрики с установленными порогами.
    Критические и warning-алерты отправляются всем CEO тенанта в Telegram
    с цветовой индикацией серьёзности.

    Зачем: обеспечивает проактивный мониторинг — CEO узнаёт о проблемах
    (падение выручки, низкая загрузка) мгновенно, а не из еженедельного отчёта.

    Args:
        ctx: Контекст arq-воркера.
    """
    from app.database import async_session_factory
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.services.analytics import AnalyticsService
    from app.services.telegram_bot import TelegramBotService

    analytics = AnalyticsService()
    tg = TelegramBotService()

    async with async_session_factory() as session:
        tenants_result = await session.execute(
            select(Tenant).where(Tenant.is_active.is_(True))
        )
        for tenant in tenants_result.scalars().all():
            alerts = await analytics.check_deviations(session, tenant.id)

            if not alerts:
                continue

            # Notify CEO about critical/warning alerts
            critical_alerts = [a for a in alerts if a.severity in ("critical", "warning")]
            if critical_alerts:
                ceo_result = await session.execute(
                    select(User)
                    .where(User.tenant_id == tenant.id)
                    .where(User.role == "ceo")
                )
                for ceo in ceo_result.scalars().all():
                    if ceo.telegram_id:
                        severity_emoji = {"critical": "🔴", "warning": "🟡"}
                        message = "📊 <b>Алерты метрик</b>\n\n"
                        for a in critical_alerts:
                            emoji = severity_emoji.get(a.severity, "ℹ️")
                            message += f"{emoji} {a.message}\n"
                        try:
                            await tg.send_message(ceo.telegram_id, message)
                        except Exception as e:
                            logger.error("Failed to notify CEO %s: %s", ceo.id, e)

            logger.info("Generated %d alerts for tenant %s", len(alerts), tenant.slug)
