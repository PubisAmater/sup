"""Pydantic-схемы для пользователей системы.

Пользователь — это учётная запись, привязанная к Telegram-аккаунту.
Роли: ``ceo`` (руководитель), ``manager`` (менеджер), ``line`` (линейный сотрудник).
Роль определяет доступ к функциям системы (дашборд CEO, начисление баллов и т.д.).
Пользователь связан с тенантом и может быть привязан к записи сотрудника.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    """Схема создания пользователя.

    Используется при регистрации через Telegram-бот.

    Attributes:
        telegram_id: Числовой ID пользователя в Telegram (уникальный).
        first_name: Имя пользователя.
        last_name: Фамилия (необязательно).
        username: Username в Telegram (необязательно).
        role: Роль в системе (``ceo``, ``manager``, ``line``). По умолчанию ``line``.
        tenant_id: UUID тенанта, к которому привязан пользователь.
    """

    telegram_id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    role: str = "line"
    tenant_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    """Схема частичного обновления пользователя.

    Attributes:
        first_name: Новое имя.
        last_name: Новая фамилия.
        username: Новый username.
        role: Новая роль.
        is_active: Флаг активности.
    """

    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    """Схема чтения пользователя (ответ API).

    Attributes:
        id: UUID пользователя.
        tenant_id: UUID тенанта.
        telegram_id: ID в Telegram.
        username: Username в Telegram.
        first_name: Имя.
        last_name: Фамилия.
        role: Роль в системе.
        is_active: Активен ли аккаунт.
        created_at: Дата регистрации.
    """

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
