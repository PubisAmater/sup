import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.decision import DecisionRead


class MeetingCreate(BaseModel):
    title: str
    description: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    participant_ids: list[uuid.UUID] = []


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
    processing_status: str
    summary: str | None
    notion_page_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MeetingDetailRead(MeetingRead):
    transcript: str | None = None
    decisions: list[DecisionRead] = []


class MeetingAnalysisResult(BaseModel):
    summary: str
    decisions: list[dict]
    tasks: list[dict]
    key_points: list[str]
    risks: list[str]
    water_percentage: float
    contradictions: list[dict] = []
