"""
Meeting model — совещание (протокол).

Центральная сущность Этапа 2. Жизненный цикл совещания:

1. Создание (status="scheduled", processing_status="pending")
   - Указываются: название, описание, дата, длительность, участники
   - Организатор = текущий пользователь

2. Загрузка транскрипции (POST /meetings/{id}/transcript)
   - Текст транскрипции из Plaud сохраняется в поле transcript
   - processing_status переходит в "processing"
   - Запускается background worker process_meeting_analysis

3. ИИ-обработка (worker process_meeting_analysis)
   - Claude API анализирует транскрипцию
   - Извлекает: решения (Decision), задачи (Task), тезисы, риски, % воды
   - Сравнивает новые решения с архивом (90 дней) на противоречия
   - Результат сохраняется в summary
   - processing_status → "completed" или "failed"

4. Синхронизация с Notion (worker sync_entity_to_notion)
   - Совещание, решения и задачи записываются в Notion базы данных
   - notion_page_id сохраняется для последующих обновлений

Статусы совещания (status):
    scheduled — запланировано
    in_progress — идёт прямо сейчас
    completed — завершено
    cancelled — отменено

Статусы обработки (processing_status):
    pending — транскрипция не загружена
    processing — Claude анализирует
    completed — анализ завершён, решения и задачи созданы
    failed — ошибка обработки (см. processing_error)
"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Meeting(Base):
    """
    Совещание (протокол).

    Attributes:
        id: UUID совещания.
        tenant_id: FK на тенант.
        title: Название (например, "Еженедельное совещание руководства").
        description: Описание / повестка дня.
        scheduled_at: Дата и время проведения.
        duration_minutes: Длительность в минутах.
        organizer_id: FK на User — кто организовал совещание.
        status: Статус совещания (scheduled/in_progress/completed/cancelled).
        transcript: Полный текст транскрипции из Plaud.
        summary: Текстовое резюме от Claude AI.
        processing_status: Статус ИИ-обработки (pending/processing/completed/failed).
        processing_error: Текст ошибки если processing_status = "failed".
        notion_page_id: ID страницы в Notion (заполняется после синхронизации).
        raw_transcript_url: URL файла транскрипции (если загружен файлом).
        created_at: Дата создания записи.
        updated_at: Дата последнего обновления.

    Relationships:
        organizer: User — организатор совещания.
        decisions: Список решений, принятых на совещании.
        participants: Список участников (через MeetingParticipant).
    """
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    scheduled_at: Mapped[datetime | None] = mapped_column()
    duration_minutes: Mapped[int | None] = mapped_column()
    organizer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    transcript: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    processing_status: Mapped[str] = mapped_column(String(50), default="pending")
    processing_error: Mapped[str | None] = mapped_column(Text)
    notion_page_id: Mapped[str | None] = mapped_column(String(255))
    raw_transcript_url: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    organizer: Mapped["User"] = relationship()  # noqa: F821
    decisions: Mapped[list["Decision"]] = relationship(back_populates="meeting")  # noqa: F821
    participants: Mapped[list["MeetingParticipant"]] = relationship(back_populates="meeting")  # noqa: F821
