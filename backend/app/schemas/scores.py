import uuid
from datetime import date, datetime

from pydantic import BaseModel


class ScoreEntryCreate(BaseModel):
    user_id: uuid.UUID
    points: int
    reason: str | None = None


class ScoreEntryRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    score_type: str
    points: int
    reason: str | None
    granted_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PeerReviewCreate(BaseModel):
    reviewee_id: uuid.UUID
    period_start: date
    period_end: date
    rating: int  # 1-5
    comment: str | None = None


class PeerReviewRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    reviewer_id: uuid.UUID
    reviewee_id: uuid.UUID
    period_start: date
    period_end: date
    rating: int
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    user_id: uuid.UUID
    first_name: str
    last_name: str | None
    total_points: int
    rank: int
