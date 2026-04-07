import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    assignee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    meeting_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("meetings.id"))
    decision_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("decisions.id"))
    status: Mapped[str] = mapped_column(String(50), default="todo")
    priority: Mapped[str] = mapped_column(String(50), default="medium")
    due_date: Mapped[date | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    assignee: Mapped["User"] = relationship()  # noqa: F821
    meeting: Mapped["Meeting | None"] = relationship()  # noqa: F821
    decision: Mapped["Decision | None"] = relationship()  # noqa: F821
