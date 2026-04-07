import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric_alert import MetricAlert
from app.models.metric_snapshot import MetricSnapshot

logger = logging.getLogger(__name__)

# Пороговые значения для алертов
THRESHOLDS = {
    "utilization_percent": {"min": 70, "max": 100, "severity": "warning"},
    "avg_check": {"min_deviation_pct": 15, "severity": "warning"},
    "revenue_monthly": {"min_deviation_pct": 10, "severity": "critical"},
    "lead_conversion": {"min": 20, "severity": "info"},
}


class AnalyticsService:
    """Monitoring and anomaly detection for business metrics."""

    async def check_deviations(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> list[MetricAlert]:
        """Check latest metrics against thresholds and historical averages."""
        alerts = []
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        # Get latest snapshots per metric
        latest_result = await session.execute(
            select(MetricSnapshot)
            .where(MetricSnapshot.tenant_id == tenant_id)
            .where(MetricSnapshot.recorded_at >= week_ago)
            .order_by(MetricSnapshot.recorded_at.desc())
        )
        latest_snapshots = latest_result.scalars().all()

        # Group by metric_name
        by_name: dict[str, list[MetricSnapshot]] = {}
        for s in latest_snapshots:
            by_name.setdefault(s.metric_name, []).append(s)

        for metric_name, snapshots in by_name.items():
            if not snapshots:
                continue

            current_value = snapshots[0].metric_value

            # Check absolute thresholds
            threshold = THRESHOLDS.get(metric_name)
            if threshold:
                if "min" in threshold and current_value < threshold["min"]:
                    alert = MetricAlert(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        metric_snapshot_id=snapshots[0].id,
                        alert_type="threshold",
                        message=f"{metric_name}: {current_value:.1f} ниже порога {threshold['min']}",
                        severity=threshold.get("severity", "info"),
                    )
                    alerts.append(alert)

            # Check deviation from average (last 30 days)
            month_ago = now - timedelta(days=30)
            avg_result = await session.execute(
                select(func.avg(MetricSnapshot.metric_value))
                .where(MetricSnapshot.tenant_id == tenant_id)
                .where(MetricSnapshot.metric_name == metric_name)
                .where(MetricSnapshot.recorded_at >= month_ago)
                .where(MetricSnapshot.recorded_at < week_ago)
            )
            avg_value = avg_result.scalar()

            if avg_value and avg_value > 0:
                deviation_pct = abs(current_value - avg_value) / avg_value * 100
                if deviation_pct > 20:
                    direction = "выше" if current_value > avg_value else "ниже"
                    alert = MetricAlert(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        metric_snapshot_id=snapshots[0].id,
                        alert_type="deviation",
                        message=f"{metric_name}: {current_value:.1f} на {deviation_pct:.0f}% {direction} среднего ({avg_value:.1f})",
                        severity="warning" if deviation_pct > 30 else "info",
                    )
                    alerts.append(alert)

        # Persist alerts
        for alert in alerts:
            session.add(alert)
        if alerts:
            await session.commit()

        return alerts

    async def get_revenue_formula(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> dict:
        """Calculate revenue formula: Chairs x Utilization x Avg Check."""
        now = datetime.now(timezone.utc)
        month_ago = now - timedelta(days=30)

        async def _latest_metric(name: str) -> float:
            result = await session.execute(
                select(MetricSnapshot.metric_value)
                .where(MetricSnapshot.tenant_id == tenant_id)
                .where(MetricSnapshot.metric_name == name)
                .order_by(MetricSnapshot.recorded_at.desc())
                .limit(1)
            )
            return result.scalar() or 0.0

        chairs = await _latest_metric("chairs_count")
        utilization = await _latest_metric("utilization_percent")
        avg_check = await _latest_metric("avg_check")

        # Норма: стоматологическое кресло 3 млн ₽/мес
        target_per_chair = 3_000_000
        target_revenue = chairs * target_per_chair
        actual_revenue = chairs * (utilization / 100) * avg_check * 22 * 8  # рабочих дней * часов

        return {
            "chairs": int(chairs),
            "utilization_percent": round(utilization, 1),
            "avg_check": round(avg_check, 0),
            "revenue": round(actual_revenue, 0),
            "target_revenue": round(target_revenue, 0),
            "gap_percent": round((1 - actual_revenue / target_revenue) * 100, 1) if target_revenue > 0 else 0,
        }
