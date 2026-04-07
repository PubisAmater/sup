"""
MetricSnapshot model — снимок бизнес-метрики.

Метрики собираются из внешних систем:
    dental_pro — Dental Pro MIS (кресла, загрузка, средний чек, приёмы)
    1c — 1С:Бухгалтерия (выручка, маржинальность, ФОТ)
    bitrix24 — Bitrix24 CRM (лиды, конверсия, сделки)

Worker collect_metrics запускается по cron и собирает метрики
для каждого активного тенанта.

Формула выручки (для стоматологии):
    Выручка = Кресла × Загрузка × Средний чек × 22 дня × 8 часов

Нормы:
    Стоматологическое кресло: 3 млн ₽/мес
    Многопрофильный кабинет: 1.5 млн ₽/мес
    Операционная: 4 млн ₽/мес
    Целевая загрузка: 85-90%
"""
import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MetricSnapshot(Base):
    """
    Снимок бизнес-метрики в определённый момент времени.

    Attributes:
        id: UUID снимка.
        tenant_id: FK на тенант (для RLS).
        source: Источник метрики (dental_pro, 1c, bitrix24).
        metric_name: Название метрики (например, "chairs_count", "utilization_percent").
        metric_value: Числовое значение метрики.
        recorded_at: Время снятия метрики.
        metadata_json: Дополнительные данные в JSON формате.
        created_at: Дата создания записи.
    """
    __tablename__ = "metric_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    source: Mapped[str] = mapped_column(String(100))
    metric_name: Mapped[str] = mapped_column(String(255), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
