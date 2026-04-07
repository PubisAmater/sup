import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MetricAlert(Base):
    __tablename__ = "metric_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    metric_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("metric_snapshots.id"))
    alert_type: Mapped[str] = mapped_column(String(50))  # deviation, trend, threshold
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(50), default="info")  # info, warning, critical
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    snapshot: Mapped["MetricSnapshot | None"] = relationship()  # noqa: F821
