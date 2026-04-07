"""Pydantic-схемы для тенантов (клиник/организаций).

Тенант — это верхнеуровневая сущность мультитенантной архитектуры.
Каждая клиника (организация) является отдельным тенантом, и все данные
(сотрудники, совещания, задачи, метрики) изолированы на уровне ``tenant_id``.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class TenantCreate(BaseModel):
    """Схема создания нового тенанта.

    Используется при регистрации новой клиники в системе.

    Attributes:
        name: Полное название организации (например, «Стоматология Улыбка»).
        slug: Уникальный короткий идентификатор (``ulybka``) для URL и внутренних нужд.
    """

    name: str
    slug: str


class TenantUpdate(BaseModel):
    """Схема частичного обновления тенанта.

    Все поля необязательные — обновляются только переданные.

    Attributes:
        name: Новое название организации.
        slug: Новый slug-идентификатор.
        is_active: Флаг активности (``False`` для деактивации тенанта).
    """

    name: str | None = None
    slug: str | None = None
    is_active: bool | None = None


class TenantRead(BaseModel):
    """Схема чтения тенанта (ответ API).

    Attributes:
        id: UUID тенанта.
        name: Название организации.
        slug: Короткий идентификатор.
        is_active: Активен ли тенант.
        created_at: Дата и время создания.
    """

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
