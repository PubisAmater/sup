"""Pydantic-схемы для решений (decisions), принятых на совещаниях.

Решение — это управленческое решение, зафиксированное по итогам совещания.
Создаётся автоматически AI-анализом транскрипции или вручную через API.
Может иметь ответственного (``assignee_id``), срок и приоритет.
Решения синхронизируются в Notion и используются для контроля исполнения.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class DecisionCreate(BaseModel):
    """Схема создания решения.

    Attributes:
        content: Текст решения (что именно было решено).
        assignee_id: UUID ответственного за исполнение (необязательно).
        due_date: Срок исполнения (необязательно).
        priority: Приоритет (``low``, ``medium``, ``high``, ``critical``). По умолчанию ``medium``.
    """

    content: str
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None
    priority: str = "medium"


class DecisionUpdate(BaseModel):
    """Схема частичного обновления решения.

    Attributes:
        content: Новый текст решения.
        assignee_id: Новый ответственный.
        due_date: Новый срок.
        priority: Новый приоритет.
        status: Новый статус (``active``, ``completed``, ``cancelled``).
    """

    content: str | None = None
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None
    priority: str | None = None
    status: str | None = None


class DecisionRead(BaseModel):
    """Схема чтения решения (ответ API).

    Attributes:
        id: UUID решения.
        tenant_id: UUID тенанта.
        meeting_id: UUID совещания, на котором принято решение.
        content: Текст решения.
        decided_by: UUID пользователя, принявшего решение.
        assignee_id: UUID ответственного.
        due_date: Срок исполнения.
        priority: Приоритет.
        status: Текущий статус.
        created_at: Дата создания.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    meeting_id: uuid.UUID
    content: str
    decided_by: uuid.UUID
    assignee_id: uuid.UUID | None
    due_date: date | None
    priority: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
