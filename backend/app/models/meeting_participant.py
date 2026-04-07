"""
MeetingParticipant model — участник совещания (M2M связь Meeting ↔ User).

Каждый участник имеет роль на совещании:
    organizer — организатор (создатель совещания)
    participant — обычный участник
    observer — наблюдатель (только слушает)

При создании совещания организатор автоматически добавляется
как участник с role_in_meeting="organizer".
"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MeetingParticipant(Base):
    """
    Участник совещания.

    Attributes:
        id: UUID записи.
        tenant_id: FK на тенант (для RLS).
        meeting_id: FK на совещание.
        user_id: FK на пользователя-участника.
        role_in_meeting: Роль на совещании (organizer/participant/observer).
        created_at: Дата добавления участника.

    Relationships:
        user: Пользователь-участник.
        meeting: Совещание.
    """
    __tablename__ = "meeting_participants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    meeting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetings.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    role_in_meeting: Mapped[str] = mapped_column(String(50), default="participant")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship()  # noqa: F821
    meeting: Mapped["Meeting"] = relationship(back_populates="participants")  # noqa: F821
