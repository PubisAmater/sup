import uuid
from datetime import datetime

from pydantic import BaseModel


class MeetingCreate(BaseModel):
    title: str
    description: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None


class MeetingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    status: str | None = None
    transcript: str | None = None
    summary: str | None = None


class MeetingRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    description: str | None
    scheduled_at: datetime | None
    duration_minutes: int | None
    organizer_id: uuid.UUID
    status: str
    summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
