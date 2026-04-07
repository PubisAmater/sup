"""
User model — учётная запись пользователя платформы.

Пользователь создаётся при первом входе через Telegram OAuth.
Каждый пользователь привязан к одному тенанту (компании) и имеет роль
в иерархии доступа.

Иерархия ролей (от высшей к низшей):
    SuperAdmin → CEO → CEO-1 → CEO-2 → Middle → Line

Авторизация:
    1. Пользователь нажимает "Войти через Telegram" на фронтенде
    2. Telegram отправляет данные пользователя (id, имя, хеш)
    3. Backend верифицирует HMAC-SHA256 хеш через bot_token
    4. Создаётся/обновляется запись User
    5. Выдаётся JWT с payload: {sub: user_id, tenant_id, role, exp}
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """
    Учётная запись пользователя.

    Attributes:
        id: UUID пользователя (генерируется при создании).
        tenant_id: FK на тенант. None только для SuperAdmin.
        telegram_id: Уникальный числовой ID из Telegram (BigInteger).
        username: Telegram username (может быть None).
        first_name: Имя из Telegram.
        last_name: Фамилия из Telegram (может быть None).
        role: Роль в системе. Одна из: superadmin, ceo, ceo_1, ceo_2, middle, line.
        is_active: Деактивированные пользователи не могут входить.
        created_at: Дата первого входа (регистрации).
        updated_at: Дата последнего обновления профиля.

    Relationships:
        tenant: Компания, к которой привязан пользователь.
        employee: Связанная запись сотрудника (если есть).
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="line")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    tenant: Mapped["Tenant | None"] = relationship(back_populates="users")  # noqa: F821
    employee: Mapped["Employee | None"] = relationship(back_populates="user")  # noqa: F821
