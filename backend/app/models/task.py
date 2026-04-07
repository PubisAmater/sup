"""
Task model — задача.

Задачи создаются:
1. Автоматически из совещаний — ИИ извлекает из транскрипции
2. Вручную — через API POST /tasks/

Статусы задачи:
    todo — к выполнению
    in_progress — в работе
    done — выполнено
    cancelled — отменено

Приоритеты:
    critical — критический (блокирует бизнес-процессы)
    high — высокий
    medium — средний (по умолчанию)
    low — низкий

Просроченные задачи:
    Задача считается просроченной если due_date < today
    и status в ("todo", "in_progress").
    Worker check_overdue_tasks ежедневно проверяет и уведомляет
    исполнителей через Telegram.

Балльная система:
    +5 баллов за задачу, выполненную в срок (auto_task_ontime)
    -3 балла за просроченную задачу (auto_task_late)
    Начисляется автоматически worker'ом auto_score_tasks.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Task(Base):
    """
    Задача.

    Attributes:
        id: UUID задачи.
        tenant_id: FK на тенант (для RLS).
        title: Краткое название задачи.
        description: Подробное описание.
        assignee_id: FK на User — исполнитель задачи.
        meeting_id: FK на Meeting — если задача создана из совещания.
        decision_id: FK на Decision — если задача создана из решения.
        status: Статус (todo/in_progress/done/cancelled).
        priority: Приоритет (critical/high/medium/low).
        due_date: Срок выполнения.
        notion_page_id: ID страницы в Notion после синхронизации.
        created_at: Дата создания.
        updated_at: Дата последнего обновления.

    Relationships:
        assignee: Исполнитель задачи (User).
        meeting: Связанное совещание (если есть).
        decision: Связанное решение (если есть).
    """
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
    notion_page_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    assignee: Mapped["User"] = relationship()  # noqa: F821
    meeting: Mapped["Meeting | None"] = relationship()  # noqa: F821
    decision: Mapped["Decision | None"] = relationship()  # noqa: F821
