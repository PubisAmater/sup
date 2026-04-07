"""Pydantic-схемы для системы баллов (scoring), peer review и лидерборда.

Система баллов мотивирует сотрудников через геймификацию:
- Автоматическое начисление за выполнение задач и подачу отчётов;
- Ручные бонусы и штрафы от руководителя;
- Лидерборд с рейтингом по суммарным баллам.

Peer review дополняет систему взаимными оценками коллег (1-5 за период).
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class ScoreEntryCreate(BaseModel):
    """Схема создания записи о начислении баллов (бонус или штраф).

    Используется эндпоинтами ``/scores/bonus`` и ``/scores/penalty``.

    Attributes:
        user_id: UUID сотрудника, которому начисляются баллы.
        points: Количество баллов (положительное число; знак определяется эндпоинтом).
        reason: Причина начисления / комментарий (необязательно).
    """

    user_id: uuid.UUID
    points: int
    reason: str | None = None


class ScoreEntryRead(BaseModel):
    """Схема чтения записи о баллах (ответ API).

    Attributes:
        id: UUID записи.
        tenant_id: UUID тенанта.
        user_id: UUID сотрудника.
        score_type: Тип начисления (``manual_bonus``, ``manual_penalty``,
            ``auto_task_ontime``, ``auto_task_late``, ``auto_report_ontime``).
        points: Количество баллов (положительное = бонус, отрицательное = штраф).
        reason: Причина начисления.
        granted_by: UUID пользователя, начислившего баллы (``null`` для автоматических).
        created_at: Дата начисления.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    score_type: str
    points: int
    reason: str | None
    granted_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PeerReviewCreate(BaseModel):
    """Схема создания peer review (взаимной оценки коллеги).

    Attributes:
        reviewee_id: UUID оцениваемого сотрудника.
        period_start: Начало оцениваемого периода.
        period_end: Конец оцениваемого периода.
        rating: Оценка от 1 (плохо) до 5 (отлично).
        comment: Текстовый комментарий к оценке (необязательно).
    """

    reviewee_id: uuid.UUID
    period_start: date
    period_end: date
    rating: int  # 1-5
    comment: str | None = None


class PeerReviewRead(BaseModel):
    """Схема чтения peer review (ответ API).

    Attributes:
        id: UUID оценки.
        tenant_id: UUID тенанта.
        reviewer_id: UUID автора оценки.
        reviewee_id: UUID оцениваемого.
        period_start: Начало периода.
        period_end: Конец периода.
        rating: Рейтинг (1-5).
        comment: Комментарий.
        created_at: Дата создания.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    reviewer_id: uuid.UUID
    reviewee_id: uuid.UUID
    period_start: date
    period_end: date
    rating: int
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    """Строка лидерборда — позиция сотрудника в рейтинге.

    Attributes:
        user_id: UUID сотрудника.
        first_name: Имя.
        last_name: Фамилия.
        total_points: Суммарное количество баллов.
        rank: Место в рейтинге (1 = лидер).
    """

    user_id: uuid.UUID
    first_name: str
    last_name: str | None
    total_points: int
    rank: int
