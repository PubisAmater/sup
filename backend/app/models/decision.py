"""
Decision model — решение, принятое на совещании.

Решения создаются двумя способами:
1. Автоматически — ИИ (Claude) извлекает из транскрипции совещания
2. Вручную — через API POST /meetings/{id}/decisions

Каждое решение привязано к совещанию и имеет:
- Ответственного за принятие (decided_by — кто принял решение)
- Исполнителя (assignee_id — кто выполняет)
- Срок выполнения (due_date)
- Приоритет (high/medium/low)

При ИИ-обработке совещания Claude также проверяет новые решения
на противоречия с архивом решений за последние 90 дней.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Decision(Base):
    """
    Решение совещания.

    Attributes:
        id: UUID решения.
        tenant_id: FK на тенант (для RLS).
        meeting_id: FK на совещание, на котором принято решение.
        content: Текст решения.
        decided_by: FK на User — кто принял решение (обычно CEO/организатор).
        assignee_id: FK на User — кто выполняет решение (исполнитель).
        due_date: Срок выполнения. Может извлекаться из транскрипции Claude.
        priority: Приоритет (high/medium/low).
        status: Статус решения (active/completed/cancelled).
        notion_page_id: ID страницы в Notion после синхронизации.
        created_at: Дата создания.

    Relationships:
        meeting: Совещание, на котором принято решение.
        decided_by_user: Кто принял решение.
        assignee: Кто выполняет решение.
    """
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    meeting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetings.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    decided_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    due_date: Mapped[date | None] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(50), default="medium")
    status: Mapped[str] = mapped_column(String(50), default="active")
    notion_page_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    meeting: Mapped["Meeting"] = relationship(back_populates="decisions")  # noqa: F821
    decided_by_user: Mapped["User"] = relationship(foreign_keys=[decided_by])  # noqa: F821
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assignee_id])  # noqa: F821
