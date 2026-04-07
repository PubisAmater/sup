"""
ScoreEntry model — запись в балльно-рейтинговой системе.

Баллы начисляются автоматически и вручную:

Автоматические баллы (workers/scores.py):
    auto_task_ontime: +5 — задача выполнена в срок
    auto_task_late: -3 — задача просрочена
    auto_report_ontime: +3 — отчёт подан вовремя
    auto_report_late: -2 — отчёт подан с просрочкой
    auto_metric_above: +2 — метрика выше плана
    auto_metric_below: -1 — метрика ниже плана

Ручные баллы (CEO через Telegram-бот или API):
    manual_bonus: +N — CEO начисляет премию с указанием причины
    manual_penalty: -N — CEO начисляет штраф с указанием причины

Peer review (раз в 2 недели):
    peer_review: рейтинг 1-5 от коллег (хранится в PeerReview)

Лидерборд: сумма всех points по user_id, отсортировано по убыванию.
"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScoreEntry(Base):
    """
    Запись баллов сотрудника.

    Attributes:
        id: UUID записи.
        tenant_id: FK на тенант (для RLS).
        user_id: FK на User — кому начислены баллы.
        score_type: Тип начисления (auto_task_ontime, manual_bonus и т.д.).
        points: Количество баллов (положительное = бонус, отрицательное = штраф).
        reason: Причина начисления (текстовое описание).
        granted_by: FK на User — кто начислил (None для автоматических).
        created_at: Дата начисления.

    Relationships:
        user: Сотрудник, которому начислены баллы.
        granter: Кто начислил (только для ручных бонусов/штрафов).
    """
    __tablename__ = "score_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    score_type: Mapped[str] = mapped_column(String(100))
    points: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821
    granter: Mapped["User | None"] = relationship(foreign_keys=[granted_by])  # noqa: F821
