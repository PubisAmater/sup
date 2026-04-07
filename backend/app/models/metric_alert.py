"""
MetricAlert model — алерт при отклонении метрики.

Алерты генерируются AnalyticsService.check_deviations() когда:
1. Метрика ниже абсолютного порога (threshold)
   Пример: загрузка кресел < 70%
2. Метрика отклоняется от среднего за 30 дней более чем на 20% (deviation)
   Пример: средний чек упал на 25%
3. Обнаружен негативный тренд (trend)
   Пример: снижение лидов на 15% за 2 недели

Уровни серьёзности:
    info — информационный (отклонение < 20%)
    warning — предупреждение (отклонение 20-30% или ниже порога)
    critical — критический (отклонение > 30% или выручка ниже плана)

CEO получает уведомления о warning и critical алертах в Telegram.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MetricAlert(Base):
    """
    Алерт при отклонении бизнес-метрики.

    Attributes:
        id: UUID алерта.
        tenant_id: FK на тенант (для RLS).
        metric_snapshot_id: FK на снимок метрики, вызвавший алерт.
        alert_type: Тип алерта (deviation/trend/threshold).
        message: Текст алерта на русском языке.
        severity: Уровень серьёзности (info/warning/critical).
        is_resolved: Помечен ли алерт как решённый.
        created_at: Дата создания.

    Relationships:
        snapshot: Снимок метрики, вызвавший алерт.
    """
    __tablename__ = "metric_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    metric_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("metric_snapshots.id"))
    alert_type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(50), default="info")
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    snapshot: Mapped["MetricSnapshot | None"] = relationship()  # noqa: F821
