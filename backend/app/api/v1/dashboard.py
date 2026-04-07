from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.employee import Employee
from app.models.meeting import Meeting
from app.models.task import Task

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)
    today = date.today()

    # Employees count
    employees_result = await session.execute(
        select(func.count(Employee.id)).where(Employee.is_active.is_(True))
    )
    employees_count = employees_result.scalar() or 0

    # Meetings this week
    meetings_result = await session.execute(
        select(func.count(Meeting.id))
        .where(Meeting.scheduled_at >= week_start)
        .where(Meeting.scheduled_at < week_end)
    )
    meetings_count = meetings_result.scalar() or 0

    # Tasks in progress
    tasks_in_progress_result = await session.execute(
        select(func.count(Task.id))
        .where(Task.status.in_(["todo", "in_progress"]))
    )
    tasks_in_progress = tasks_in_progress_result.scalar() or 0

    # Overdue tasks
    overdue_result = await session.execute(
        select(func.count(Task.id))
        .where(Task.due_date < today)
        .where(Task.status.in_(["todo", "in_progress"]))
    )
    overdue_count = overdue_result.scalar() or 0

    return {
        "employees_count": employees_count,
        "meetings_this_week": meetings_count,
        "tasks_in_progress": tasks_in_progress,
        "overdue_tasks": overdue_count,
    }
