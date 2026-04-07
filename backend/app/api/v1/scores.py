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
