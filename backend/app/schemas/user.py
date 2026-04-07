import uuid
from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    telegram_id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    role: str = "line"
    tenant_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    telegram_id: int
    username: str | None
    first_name: str
    last_name: str | None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
