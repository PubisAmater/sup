"""Pydantic-схемы для совещаний и результатов AI-анализа.

Совещание — центральная сущность системы. Содержит метаданные (название,
дата, участники), транскрипцию, AI-саммари и привязки к решениям/задачам.
Статус обработки (``processing_status``) отслеживает прогресс AI-анализа.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.decision import DecisionRead


class MeetingCreate(BaseModel):
    """Схема создания совещания.

    Attributes:
        title: Название совещания.
        description: Описание / повестка дня (необязательно).
        scheduled_at: Дата и время проведения.
        duration_minutes: Планируемая длительность в минутах.
        participant_ids: Список UUID участников (помимо организатора).
    """

    title: str
    description: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    participant_ids: list[uuid.UUID] = []


class MeetingUpdate(BaseModel):
    """Схема частичного обновления совещания.

    Attributes:
        title: Новое название.
        description: Новое описание.
        scheduled_at: Новая дата/время.
        duration_minutes: Новая длительность.
        status: Новый статус (``scheduled``, ``completed``, ``cancelled``).
        transcript: Текст транскрипции.
        summary: AI-саммари совещания.
    """

    title: str | None = None
    description: str | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = None
    status: str | None = None
    transcript: str | None = None
    summary: str | None = None


class MeetingRead(BaseModel):
    """Схема чтения совещания (краткая, без транскрипции).

    Используется в списках совещаний, где транскрипция не нужна.

    Attributes:
        id: UUID совещания.
        tenant_id: UUID тенанта.
        title: Название.
        description: Описание.
        scheduled_at: Дата/время проведения.
        duration_minutes: Длительность.
        organizer_id: UUID организатора.
        status: Статус совещания.
        processing_status: Статус AI-обработки (``pending``, ``processing``, ``completed``, ``failed``).
        summary: AI-саммари (если анализ завершён).
        notion_page_id: ID страницы в Notion (если синхронизировано).
        created_at: Дата создания.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    description: str | None
    scheduled_at: datetime | None
    duration_minutes: int | None
    organizer_id: uuid.UUID
    status: str
    processing_status: str
    summary: str | None
    notion_page_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MeetingDetailRead(MeetingRead):
    """Расширенная схема совещания с транскрипцией и решениями.

    Используется при детальном просмотре конкретного совещания.

    Attributes:
        transcript: Полный текст транскрипции.
        decisions: Список решений, принятых на совещании.
    """

    transcript: str | None = None
    decisions: list[DecisionRead] = []


class MeetingAnalysisResult(BaseModel):
    """Результат AI-анализа транскрипции совещания.

    Возвращается сервисом Claude после обработки транскрипции.
    Содержит структурированные данные для создания решений и задач в БД.

    Attributes:
        summary: Краткое саммари совещания.
        decisions: Список решений (словари с ключами ``content``, ``priority``, ``due_date_hint``).
        tasks: Список задач (словари с ключами ``title``, ``description``, ``priority``, ``due_date_hint``).
        key_points: Ключевые тезисы обсуждения.
        risks: Выявленные риски.
        water_percentage: Процент «воды» в разговоре (0-100).
        contradictions: Противоречия с предыдущими решениями.
    """

    summary: str
    decisions: list[dict]
    tasks: list[dict]
    key_points: list[str]
    risks: list[str]
    water_percentage: float
    contradictions: list[dict] = []
