"""
Tenant model — корневая сущность мультитенантной архитектуры.

Каждый тенант представляет одну компанию-клиента платформы СУП.
Все остальные сущности (пользователи, сотрудники, совещания и т.д.)
привязаны к тенанту через поле tenant_id.

Первый клиент: ГК «Диадент» — сеть стоматологических клиник, СПб.

Мультитенантность реализована через PostgreSQL Row Level Security (RLS).
Политики RLS фильтруют строки по значению current_setting('app.current_tenant'),
которое устанавливается в начале каждого запроса через dependencies.py.

Таблица tenants НЕ имеет RLS — к ней имеет доступ только SuperAdmin.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tenant(Base):
    """
    Компания-клиент платформы СУП.

    Attributes:
        id: Уникальный идентификатор тенанта (UUID v4).
        name: Полное название компании (например, "ГК Диадент").
        slug: URL-friendly идентификатор (например, "diadent"). Уникальный.
        is_active: Флаг активности. Деактивированные тенанты не могут входить в систему.
        created_at: Дата создания записи (заполняется автоматически).
        updated_at: Дата последнего обновления (заполняется автоматически).

    Relationships:
        users: Все пользователи, привязанные к этому тенанту.
    """
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="tenant")  # noqa: F821
