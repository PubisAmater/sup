"""
WeeklyReport model — еженедельный отчёт топ-менеджера.

Каждый понедельник топ-менеджеры (CEO-1, CEO-2) подают отчёт
за прошедшую неделю через веб-форму.

Содержание отчёта:
    - completed_tasks: Завершённые задачи с итогами (текст)
    - metrics_json: Ключевые метрики отдела (текст/JSON)
    - requests: Запросы управленческих решений к CEO
    - attachments_json: Ссылки на вложения (PDF, скриншоты)

Жизненный цикл:
    1. Топ-менеджер создаёт отчёт (status="draft")
    2. Заполняет поля через форму /dashboard/reports/new
    3. Нажимает "Подать отчёт" (status="submitted", submitted_at заполняется)
    4. Worker deliver_report_to_ceo отправляет отчёт CEO в Telegram по блокам
    5. Worker generate_audio_summary генерирует аудио-саммари через SpeechKit
    6. CEO помечает как рассмотренный (status="reviewed")

Балльная система:
    +3 балла за своевременную подачу (auto_report_ontime)
    -2 балла за просрочку (auto_report_late)
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WeeklyReport(Base):
    """
    Еженедельный отчёт топ-менеджера.

    Attributes:
        id: UUID отчёта.
        tenant_id: FK на тенант (для RLS).
        user_id: FK на User — автор отчёта.
        period_start: Начало отчётного периода (понедельник).
        period_end: Конец отчётного периода (воскресенье).
        completed_tasks: Завершённые задачи с итогами.
        metrics_json: Ключевые метрики в текстовом или JSON формате.
        requests: Запросы управленческих решений к CEO.
        attachments_json: JSON массив ссылок на вложения.
        status: Статус (draft/submitted/reviewed).
        submitted_at: Дата и время подачи отчёта.
        created_at: Дата создания.
        updated_at: Дата последнего обновления.

    Relationships:
        user: Автор отчёта.
    """
    __tablename__ = "weekly_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    completed_tasks: Mapped[str | None] = mapped_column(Text)
    metrics_json: Mapped[str | None] = mapped_column(Text)
    requests: Mapped[str | None] = mapped_column(Text)
    attachments_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    submitted_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship()  # noqa: F821
