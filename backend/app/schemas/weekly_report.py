import uuid
from datetime import date, datetime

from pydantic import BaseModel


class ReportCreate(BaseModel):
    period_start: date
    period_end: date
    completed_tasks: str | None = None
    metrics_json: str | None = None
    requests: str | None = None
    attachments_json: str | None = None


class ReportUpdate(BaseModel):
    completed_tasks: str | None = None
    metrics_json: str | None = None
    requests: str | None = None
    attachments_json: str | None = None
    status: str | None = None


class ReportRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    period_start: date
    period_end: date
    completed_tasks: str | None
    metrics_json: str | None
    requests: str | None
    attachments_json: str | None
    status: str
    submitted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
