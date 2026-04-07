import uuid
from datetime import date, datetime

from pydantic import BaseModel


class DecisionCreate(BaseModel):
    content: str
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None
    priority: str = "medium"


class DecisionUpdate(BaseModel):
    content: str | None = None
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None
    priority: str | None = None
    status: str | None = None


class DecisionRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    meeting_id: uuid.UUID
    content: str
    decided_by: uuid.UUID
    assignee_id: uuid.UUID | None
    due_date: date | None
    priority: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
