"""Pydantic-схемы для задач.

Задача — это единица работы, назначенная исполнителю. Может быть создана
вручную или автоматически из AI-анализа совещания. Связана с совещанием
и/или решением. Отслеживается по статусу (``todo`` -> ``in_progress`` -> ``done``)
и приоритету. Просроченные задачи генерируют уведомления и влияют на баллы.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class TaskCreate(BaseModel):
    """Схема создания задачи.

    Attributes:
        title: Название задачи (краткое описание).
        description: Подробное описание задачи (необязательно).
        assignee_id: UUID исполнителя (обязательно).
        meeting_id: UUID совещания-источника (необязательно).
        decision_id: UUID решения, из которого создана задача (необязательно).
        priority: Приоритет (``low``, ``medium``, ``high``, ``critical``).
        due_date: Крайний срок выполнения.
    """

    title: str
    description: str | None = None
    assignee_id: uuid.UUID
    meeting_id: uuid.UUID | None = None
    decision_id: uuid.UUID | None = None
    priority: str = "medium"
    due_date: date | None = None


class TaskUpdate(BaseModel):
    """Схема частичного обновления задачи.

    Attributes:
        title: Новое название.
        description: Новое описание.
        assignee_id: Новый исполнитель.
        status: Новый статус (``todo``, ``in_progress``, ``done``).
        priority: Новый приоритет.
        due_date: Новый крайний срок.
    """

    title: str | None = None
    description: str | None = None
    assignee_id: uuid.UUID | None = None
    status: str | None = None
    priority: str | None = None
    due_date: date | None = None


class TaskRead(BaseModel):
    """Схема чтения задачи (ответ API).

    Attributes:
        id: UUID задачи.
        tenant_id: UUID тенанта.
        title: Название.
        description: Описание.
        assignee_id: UUID исполнителя.
        meeting_id: UUID связанного совещания.
        decision_id: UUID связанного решения.
        status: Текущий статус.
        priority: Приоритет.
        due_date: Крайний срок.
        notion_page_id: ID страницы в Notion (если синхронизировано).
        created_at: Дата создания.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    description: str | None
    assignee_id: uuid.UUID
    meeting_id: uuid.UUID | None
    decision_id: uuid.UUID | None
    status: str
    priority: str
    due_date: date | None
    notion_page_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
