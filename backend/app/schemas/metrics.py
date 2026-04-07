import uuid
from datetime import datetime

from pydantic import BaseModel


class MetricSnapshotCreate(BaseModel):
    source: str
    metric_name: str
    metric_value: float
    recorded_at: datetime
    metadata_json: str | None = None


class MetricSnapshotRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    metric_name: str
    metric_value: float
    recorded_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class MetricAlertRead(BaseModel):
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
    chairs: int
    utilization_percent: float
    avg_check: float
    revenue: float
    target_revenue: float
    gap_percent: float
