import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    meeting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetings.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    decided_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    meeting: Mapped["Meeting"] = relationship(back_populates="decisions")  # noqa: F821
    decided_by_user: Mapped["User"] = relationship()  # noqa: F821
