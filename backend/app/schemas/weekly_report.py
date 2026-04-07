"""Pydantic-схемы для еженедельных отчётов сотрудников.

Еженедельный отчёт содержит информацию о выполненных задачах, метриках,
запросах управленческих решений и вложениях. Подаётся сотрудником раз в неделю,
после чего доставляется CEO через Telegram (текст + аудио-саммари).
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class ReportCreate(BaseModel):
    """Схема создания еженедельного отчёта.

    Attributes:
        period_start: Дата начала отчётного периода (понедельник).
        period_end: Дата окончания отчётного периода (воскресенье).
        completed_tasks: Текстовое описание выполненных задач.
        metrics_json: Метрики в формате JSON-строки.
        requests: Запросы управленческих решений от CEO.
        attachments_json: Вложения (ссылки/файлы) в формате JSON-строки.
    """

    period_start: date
    period_end: date
    completed_tasks: str | None = None
    metrics_json: str | None = None
    requests: str | None = None
    attachments_json: str | None = None


class ReportUpdate(BaseModel):
    """Схема частичного обновления отчёта.

    Attributes:
        completed_tasks: Обновлённое описание задач.
        metrics_json: Обновлённые метрики.
        requests: Обновлённые запросы.
        attachments_json: Обновлённые вложения.
        status: Новый статус (``draft``, ``submitted``).
    """

    completed_tasks: str | None = None
    metrics_json: str | None = None
    requests: str | None = None
    attachments_json: str | None = None
    status: str | None = None


class ReportRead(BaseModel):
    """Схема чтения отчёта (ответ API).

    Attributes:
        id: UUID отчёта.
        tenant_id: UUID тенанта.
        user_id: UUID автора отчёта.
        period_start: Начало отчётного периода.
        period_end: Конец отчётного периода.
        completed_tasks: Выполненные задачи.
        metrics_json: Метрики.
        requests: Запросы управленческих решений.
        attachments_json: Вложения.
        status: Статус (``draft`` или ``submitted``).
        submitted_at: Время подачи (``null`` для черновиков).
        created_at: Дата создания.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    period_start: date
    period_end: date
    completed_tasks: str | None
    metrics_json: str | None
    requests: str | None
    attachments_json: str | None
    status: str
    submitted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
