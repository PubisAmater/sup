"""Pydantic-схемы для бизнес-метрик, алертов и формулы выручки.

Метрики собираются из внешних систем (DentalPro, 1C, Bitrix24) и хранятся
как снимки (snapshots) с указанием источника, имени метрики, значения и времени.
Алерты генерируются при отклонениях от пороговых значений.
Формула выручки декомпозирует доход: кресла * загрузка * средний чек.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class MetricSnapshotCreate(BaseModel):
    """Схема создания снимка метрики.

    Attributes:
        source: Система-источник (``dental_pro``, ``1c``, ``bitrix24``).
        metric_name: Имя метрики (``revenue_monthly``, ``utilization_percent`` и т.д.).
        metric_value: Числовое значение метрики.
        recorded_at: Время фиксации значения.
        metadata_json: Дополнительные данные в формате JSON-строки.
    """

    source: str
    metric_name: str
    metric_value: float
    recorded_at: datetime
    metadata_json: str | None = None


class MetricSnapshotRead(BaseModel):
    """Схема чтения снимка метрики (ответ API).

    Attributes:
        id: UUID снимка.
        tenant_id: UUID тенанта.
        source: Система-источник.
        metric_name: Имя метрики.
        metric_value: Значение.
        recorded_at: Время фиксации.
        created_at: Дата создания записи в БД.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    metric_name: str
    metric_value: float
    recorded_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class MetricAlertRead(BaseModel):
    """Схема чтения алерта по метрике (ответ API).

    Attributes:
        id: UUID алерта.
        tenant_id: UUID тенанта.
        metric_snapshot_id: UUID снимка метрики, вызвавшего алерт.
        alert_type: Тип алерта (``deviation``, ``threshold`` и т.д.).
        message: Текстовое описание проблемы.
        severity: Серьёзность (``critical``, ``warning``, ``info``).
        is_resolved: Разрешён ли алерт.
        created_at: Дата создания.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    metric_snapshot_id: uuid.UUID | None
    alert_type: str
    message: str
    severity: str
    is_resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RevenueFormulaRead(BaseModel):
    """Декомпозиция формулы выручки клиники.

    Формула: ``revenue = chairs * utilization_percent * avg_check``.
    Сравнивает фактическую выручку с плановой для выявления узких мест.

    Attributes:
        chairs: Количество стоматологических кресел.
        utilization_percent: Процент загрузки кресел (0-100).
        avg_check: Средний чек в рублях.
        revenue: Фактическая выручка за период.
        target_revenue: Плановая (целевая) выручка.
        gap_percent: Разрыв между фактом и планом в процентах.
    """

    chairs: int
    utilization_percent: float
    avg_check: float
    revenue: float
    target_revenue: float
    gap_percent: float
