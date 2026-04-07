"""Агрегированная статистика для дашборда CEO.

Модуль предоставляет единый эндпоинт, возвращающий ключевые показатели
для главного экрана: количество сотрудников, совещания текущей недели,
задачи в работе и просроченные задачи. Данные используются фронтендом
для отображения виджетов дашборда руководителя.
"""

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
    """Возвращает сводную статистику для дашборда CEO.

    Собирает агрегированные данные из нескольких таблиц одним запросом:
    - ``employees_count`` — число активных сотрудников в системе;
    - ``meetings_this_week`` — количество совещаний, запланированных на текущую неделю;
    - ``tasks_in_progress`` — задачи в статусах ``todo`` и ``in_progress``;
    - ``overdue_tasks`` — просроченные незавершённые задачи.

    Зачем: CEO видит ключевые цифры сразу при входе в систему, без необходимости
    переходить в отдельные разделы. Это ускоряет принятие управленческих решений.

    Args:
        session: Асинхронная сессия SQLAlchemy (инъекция через Depends).
        current_user: Данные текущего пользователя из JWT-токена.

    Returns:
        dict: Словарь с четырьмя числовыми метриками для виджетов дашборда.
    """
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
