import uuid
from datetime import datetime

from arq.connections import ArqRedis, create_pool
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.dependencies import get_current_user, get_db
from app.models.decision import Decision
from app.models.meeting import Meeting
from app.models.meeting_participant import MeetingParticipant
from app.models.task import Task
from app.schemas.decision import DecisionCreate, DecisionRead
from app.schemas.meeting import MeetingCreate, MeetingDetailRead, MeetingRead, MeetingUpdate
from app.schemas.task import TaskRead

router = APIRouter(prefix="/meetings", tags=["meetings"])


async def _get_arq_pool() -> ArqRedis:
    settings = get_settings()
    return await create_pool(settings.redis_url)


@router.get("/", response_model=list[MeetingRead])
async def list_meetings(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    organizer_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = select(Meeting)
    if status_filter:
        query = query.where(Meeting.status == status_filter)
    if organizer_id:
        query = query.where(Meeting.organizer_id == organizer_id)
    if date_from:
        query = query.where(Meeting.scheduled_at >= date_from)
    if date_to:
        query = query.where(Meeting.scheduled_at <= date_to)
    query = query.order_by(Meeting.scheduled_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{meeting_id}", response_model=MeetingDetailRead)
async def get_meeting(
    meeting_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await session.execute(
        select(Meeting)
        .options(selectinload(Meeting.decisions))
        .where(Meeting.id == meeting_id)
    )
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
    tenant_id = uuid.UUID(current_user["tenant_id"])
    user_id = uuid.UUID(current_user["sub"])

    meeting = Meeting(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        organizer_id=user_id,
        title=data.title,
        description=data.description,
        scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes,
    )
    session.add(meeting)

    # Add organizer as participant
    session.add(MeetingParticipant(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        meeting_id=meeting.id,
        user_id=user_id,
        role_in_meeting="organizer",
    ))

    # Add other participants
    for pid in data.participant_ids:
        if pid != user_id:
            session.add(MeetingParticipant(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                meeting_id=meeting.id,
                user_id=pid,
                role_in_meeting="participant",
            ))

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


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await session.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    await session.delete(meeting)
    await session.commit()


@router.post("/{meeting_id}/transcript", response_model=MeetingRead)
async def upload_transcript(
    meeting_id: uuid.UUID,
    transcript: str = Body(..., embed=True),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await session.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    meeting.transcript = transcript
    meeting.processing_status = "pending"
    meeting.processing_error = None
    await session.commit()

    # Enqueue AI analysis
    try:
        pool = await _get_arq_pool()
        await pool.enqueue_job("process_meeting_analysis", str(meeting_id))
        meeting.processing_status = "processing"
        await session.commit()
    except Exception:
        pass  # Analysis will be triggered manually if queue unavailable

    await session.refresh(meeting)
    return meeting


@router.post("/{meeting_id}/analyze", response_model=MeetingRead)
async def trigger_analysis(
    meeting_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await session.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    if not meeting.transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No transcript to analyze",
        )

    meeting.processing_status = "processing"
    meeting.processing_error = None
    await session.commit()

    try:
        pool = await _get_arq_pool()
        await pool.enqueue_job("process_meeting_analysis", str(meeting_id))
    except Exception:
        meeting.processing_status = "failed"
        meeting.processing_error = "Failed to enqueue analysis job"
        await session.commit()

    await session.refresh(meeting)
    return meeting


@router.get("/{meeting_id}/analysis")
async def get_analysis(
    meeting_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await session.execute(
        select(Meeting)
        .options(selectinload(Meeting.decisions))
        .where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    tasks_result = await session.execute(
        select(Task).where(Task.meeting_id == meeting_id)
    )
    tasks = tasks_result.scalars().all()

    return {
        "meeting_id": str(meeting.id),
        "processing_status": meeting.processing_status,
        "processing_error": meeting.processing_error,
        "summary": meeting.summary,
        "decisions": [DecisionRead.model_validate(d) for d in meeting.decisions],
        "tasks": [TaskRead.model_validate(t) for t in tasks],
    }


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
        assignee_id=data.assignee_id,
        due_date=data.due_date,
        priority=data.priority,
    )
    session.add(decision)
    await session.commit()
    await session.refresh(decision)
    return decision
