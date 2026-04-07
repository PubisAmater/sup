import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.decision import Decision
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreate, MeetingRead, MeetingUpdate
from app.schemas.task import DecisionCreate, DecisionRead

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("/", response_model=list[MeetingRead])
async def list_meetings(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = select(Meeting)
    if status_filter:
        query = query.where(Meeting.status == status_filter)
    query = query.order_by(Meeting.scheduled_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{meeting_id}", response_model=MeetingRead)
async def get_meeting(
    meeting_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await session.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    return meeting


@router.post("/", response_model=MeetingRead, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    data: MeetingCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    meeting = Meeting(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(current_user["tenant_id"]),
        organizer_id=uuid.UUID(current_user["sub"]),
        **data.model_dump(),
    )
    session.add(meeting)
    await session.commit()
    await session.refresh(meeting)
    return meeting


@router.patch("/{meeting_id}", response_model=MeetingRead)
async def update_meeting(
    meeting_id: uuid.UUID,
    data: MeetingUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await session.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(meeting, field, value)

    await session.commit()
    await session.refresh(meeting)
    return meeting


@router.get("/{meeting_id}/decisions", response_model=list[DecisionRead])
async def list_meeting_decisions(
    meeting_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await session.execute(
        select(Decision).where(Decision.meeting_id == meeting_id)
    )
    return result.scalars().all()


@router.post(
    "/{meeting_id}/decisions",
    response_model=DecisionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_decision(
    meeting_id: uuid.UUID,
    data: DecisionCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    decision = Decision(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(current_user["tenant_id"]),
        meeting_id=meeting_id,
        content=data.content,
        decided_by=uuid.UUID(current_user["sub"]),
    )
    session.add(decision)
    await session.commit()
    await session.refresh(decision)
    return decision
