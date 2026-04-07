"""Pydantic-схемы для сотрудников клиники.

Сотрудник — это кадровая запись, содержащая должность, отдел и дату найма.
Может быть привязана к пользователю системы (``user_id``). Используется
для кадрового учёта, фильтрации по отделам и отображения в дашборде.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class EmployeeCreate(BaseModel):
    """Схема создания сотрудника.

    Attributes:
        user_id: UUID связанного пользователя системы (необязательно).
        position: Должность (например, «стоматолог-терапевт»).
        department: Отдел (например, «терапия», «хирургия», «администрация»).
        hired_at: Дата найма.
    """

    user_id: uuid.UUID | None = None
    position: str
    department: str
    hired_at: date | None = None


class EmployeeUpdate(BaseModel):
    """Схема частичного обновления сотрудника.

    Attributes:
        position: Новая должность.
        department: Новый отдел.
        hired_at: Новая дата найма.
        is_active: Флаг активности (``False`` при увольнении).
    """

    position: str | None = None
    department: str | None = None
    hired_at: date | None = None
    is_active: bool | None = None


class EmployeeRead(BaseModel):
    """Схема чтения сотрудника (ответ API).

    Attributes:
        id: UUID записи сотрудника.
        tenant_id: UUID тенанта (клиники).
        user_id: UUID связанного пользователя.
        position: Должность.
        department: Отдел.
        hired_at: Дата найма.
        is_active: Активен ли сотрудник.
        created_at: Дата создания записи.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None
    position: str
    department: str
    hired_at: date | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
