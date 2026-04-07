"""
PeerReview model — peer-review (оценка коллег).

Проводится раз в 2 недели. Каждый сотрудник оценивает коллег
по пятибалльной шкале с текстовым комментарием.

Оценка включает:
    rating: 1-5 баллов
    comment: Текстовый отзыв (что хорошо, что улучшить)

Горизонтальный контроль:
    Сотрудники также могут подавать жалобы на коллег
    через бота или веб-форму (отдельный процесс).

API: POST /peer-reviews/ — создание оценки.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PeerReview(Base):
    """
    Оценка коллеги (peer review).

    Attributes:
        id: UUID записи.
        tenant_id: FK на тенант (для RLS).
        reviewer_id: FK на User — кто оценивает.
        reviewee_id: FK на User — кого оценивают.
        period_start: Начало оцениваемого периода.
        period_end: Конец оцениваемого периода.
        rating: Оценка от 1 до 5.
        comment: Текстовый отзыв.
        created_at: Дата создания оценки.

    Relationships:
        reviewer: Кто оценивает.
        reviewee: Кого оценивают.
    """
    __tablename__ = "peer_reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    reviewee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    reviewer: Mapped["User"] = relationship(foreign_keys=[reviewer_id])  # noqa: F821
    reviewee: Mapped["User"] = relationship(foreign_keys=[reviewee_id])  # noqa: F821
