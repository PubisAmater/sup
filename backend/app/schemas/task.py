import uuid
from datetime import date, datetime

from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    assignee_id: uuid.UUID
    meeting_id: uuid.UUID | None = None
    decision_id: uuid.UUID | None = None
    priority: str = "medium"
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_id: uuid.UUID | None = None
    status: str | None = None
    priority: str | None = None
    due_date: date | None = None


class TaskRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    description: str | None
    assignee_id: uuid.UUID
    meeting_id: uuid.UUID | None
    decision_id: uuid.UUID | None
    status: str
    priority: str
    due_date: date | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionCreate(BaseModel):
    content: str
    meeting_id: uuid.UUID


class DecisionRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    meeting_id: uuid.UUID
    content: str
    decided_by: uuid.UUID
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
