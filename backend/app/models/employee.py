"""
Employee model — сотрудник компании.

Отделена от User, потому что:
- User — учётная запись для входа (Telegram OAuth)
- Employee — кадровая запись (должность, отдел, дата найма)

Один User может не иметь Employee (если ещё не оформлен).
Один Employee может не иметь User (если ещё не зарегистрирован в системе).

Связь User ↔ Employee — one-to-one через user_id.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Employee(Base):
    """
    Кадровая запись сотрудника.

    Attributes:
        id: UUID записи.
        tenant_id: FK на тенант (компанию). Обязательное — RLS фильтрует по нему.
        user_id: FK на учётную запись User. Unique — один Employee = один User.
        position: Должность (например, "Стоматолог-терапевт").
        department: Отдел (например, "Клиника", "Маркетинг", "Финансы").
        hired_at: Дата приёма на работу.
        is_active: False = уволен.
        created_at: Дата создания записи в системе.
        updated_at: Дата последнего обновления.

    Relationships:
        user: Связанная учётная запись (если зарегистрирован).
    """
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), unique=True)
    position: Mapped[str] = mapped_column(String(255))
    department: Mapped[str] = mapped_column(String(255))
    hired_at: Mapped[date | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    user: Mapped["User | None"] = relationship(back_populates="employee")  # noqa: F821
