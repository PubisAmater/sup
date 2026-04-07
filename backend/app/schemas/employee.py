import uuid
from datetime import date, datetime

from pydantic import BaseModel


class EmployeeCreate(BaseModel):
    user_id: uuid.UUID | None = None
    position: str
    department: str
    hired_at: date | None = None


class EmployeeUpdate(BaseModel):
    position: str | None = None
    department: str | None = None
    hired_at: date | None = None
    is_active: bool | None = None


class EmployeeRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None
    position: str
    department: str
    hired_at: date | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
