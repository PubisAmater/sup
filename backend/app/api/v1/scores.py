"""Лидерборд сотрудников, ручные бонусы и штрафы.

Модуль реализует систему баллов (геймификация) для мотивации сотрудников:
- Лидерборд — рейтинг сотрудников по суммарным баллам;
- История баллов конкретного сотрудника;
- Ручное начисление бонусов (положительные баллы) руководителем;
- Ручное начисление штрафов (отрицательные баллы) руководителем.

Автоматическое начисление баллов за выполнение задач и подачу отчётов
выполняется воркерами ``auto_score_tasks`` и ``auto_score_reports``.
"""

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.score_entry import ScoreEntry
from app.models.user import User
from app.schemas.scores import LeaderboardEntry, ScoreEntryCreate, ScoreEntryRead

router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Возвращает лидерборд — рейтинг сотрудников по суммарным баллам.

    Агрегирует все записи баллов (автоматические и ручные) для каждого
    пользователя, сортирует по убыванию и присваивает ранг (место).
    Используется на дашборде для визуализации вовлечённости команды.

    Args:
        limit: Максимальное количество позиций в рейтинге (1-100).
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        list[LeaderboardEntry]: Рейтинг с именами, баллами и рангами.
    """
    result = await session.execute(
        select(
            ScoreEntry.user_id,
            User.first_name,
            User.last_name,
            func.sum(ScoreEntry.points).label("total_points"),
        )
        .join(User, ScoreEntry.user_id == User.id)
        .group_by(ScoreEntry.user_id, User.first_name, User.last_name)
        .order_by(func.sum(ScoreEntry.points).desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        LeaderboardEntry(
            user_id=row.user_id,
            first_name=row.first_name,
            last_name=row.last_name,
            total_points=row.total_points or 0,
            rank=i + 1,
        )
        for i, row in enumerate(rows)
    ]


@router.get("/user/{user_id}", response_model=list[ScoreEntryRead])
async def get_user_scores(
    user_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Возвращает историю начислений баллов для конкретного сотрудника.

    Показывает все записи (бонусы, штрафы, автоначисления) в хронологическом
    порядке (новые сверху). Используется в профиле сотрудника для прозрачности
    системы мотивации.

    Args:
        user_id: UUID сотрудника.
        offset: Смещение для пагинации.
        limit: Максимум записей (1-100).
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        list[ScoreEntryRead]: Записи начислений баллов.
    """
    result = await session.execute(
        select(ScoreEntry)
        .where(ScoreEntry.user_id == user_id)
        .order_by(ScoreEntry.created_at.desc())
        .offset(offset).limit(limit)
    )
    return result.scalars().all()


@router.post("/bonus", response_model=ScoreEntryRead, status_code=status.HTTP_201_CREATED)
async def grant_bonus(
    data: ScoreEntryCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Начисляет бонусные баллы сотруднику.

    Позволяет CEO или руководителю вручную наградить сотрудника за
    особые достижения (инициативу, помощь коллегам и т.д.).
    Баллы всегда положительные — при отрицательном значении возвращает 400.
    Записывается кто начислил (``granted_by`` из JWT).

    Args:
        data: UUID сотрудника, количество баллов и причина.
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        ScoreEntryRead: Созданная запись о бонусе.

    Raises:
        HTTPException: 400, если баллы <= 0.
    """
    if data.points <= 0:
        raise HTTPException(status_code=400, detail="Bonus points must be positive")

    entry = ScoreEntry(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(current_user["tenant_id"]),
        user_id=data.user_id,
        score_type="manual_bonus",
        points=abs(data.points),
        reason=data.reason,
        granted_by=uuid.UUID(current_user["sub"]),
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


@router.post("/penalty", response_model=ScoreEntryRead, status_code=status.HTTP_201_CREATED)
async def grant_penalty(
    data: ScoreEntryCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Начисляет штрафные баллы сотруднику.

    Позволяет руководителю вручную назначить штраф за нарушения
    (опоздания, несоблюдение регламентов и т.д.). Баллы сохраняются
    с отрицательным знаком (``-abs(points)``). Записывается кто назначил штраф.

    Args:
        data: UUID сотрудника, количество баллов и причина.
        session: Асинхронная сессия БД.
        current_user: Данные текущего пользователя из JWT.

    Returns:
        ScoreEntryRead: Созданная запись о штрафе.
    """
    entry = ScoreEntry(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(current_user["tenant_id"]),
        user_id=data.user_id,
        score_type="manual_penalty",
        points=-abs(data.points),
        reason=data.reason,
        granted_by=uuid.UUID(current_user["sub"]),
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry
