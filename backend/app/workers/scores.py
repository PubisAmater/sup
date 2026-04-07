import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import select, func

from app.config import get_settings

logger = logging.getLogger(__name__)

# Баллы за разные события
SCORE_VALUES = {
    "auto_task_ontime": 5,
    "auto_task_late": -3,
    "auto_report_ontime": 3,
    "auto_report_late": -2,
    "auto_metric_above": 2,
    "auto_metric_below": -1,
}


async def auto_score_tasks(ctx: dict) -> None:
    """Auto-score users for completed tasks (on-time vs late)."""
    from app.database import async_session_factory
    from app.models.score_entry import ScoreEntry
    from app.models.task import Task

    today = date.today()
    yesterday = today - timedelta(days=1)

    async with async_session_factory() as session:
        # Find tasks completed yesterday
        result = await session.execute(
            select(Task)
            .where(Task.status == "done")
            .where(Task.updated_at >= str(yesterday))
            .where(Task.updated_at < str(today))
        )
        tasks = result.scalars().all()

        entries = []
        for task in tasks:
            if task.due_date and task.due_date >= yesterday:
                # On time
                entries.append(ScoreEntry(
                    id=uuid.uuid4(),
                    tenant_id=task.tenant_id,
                    user_id=task.assignee_id,
                    score_type="auto_task_ontime",
                    points=SCORE_VALUES["auto_task_ontime"],
                    reason=f"Задача выполнена в срок: {task.title[:100]}",
                ))
            elif task.due_date and task.due_date < yesterday:
                # Late
                entries.append(ScoreEntry(
                    id=uuid.uuid4(),
                    tenant_id=task.tenant_id,
                    user_id=task.assignee_id,
                    score_type="auto_task_late",
                    points=SCORE_VALUES["auto_task_late"],
                    reason=f"Задача выполнена с просрочкой: {task.title[:100]}",
                ))

        for entry in entries:
            session.add(entry)
        if entries:
            await session.commit()
            logger.info("Auto-scored %d task completions", len(entries))


async def auto_score_reports(ctx: dict) -> None:
    """Auto-score users for timely/late report submissions."""
    from app.database import async_session_factory
    from app.models.score_entry import ScoreEntry
    from app.models.weekly_report import WeeklyReport

    today = date.today()
    # Reports are due by Monday for previous week
    if today.weekday() != 0:  # Only run on Mondays
        return

    week_end = today - timedelta(days=1)  # Sunday
    week_start = week_end - timedelta(days=6)  # Monday

    async with async_session_factory() as session:
        result = await session.execute(
            select(WeeklyReport)
            .where(WeeklyReport.period_start == week_start)
            .where(WeeklyReport.period_end == week_end)
            .where(WeeklyReport.status == "submitted")
        )
        reports = result.scalars().all()

        entries = []
        for report in reports:
            if report.submitted_at and report.submitted_at.date() <= today:
                entries.append(ScoreEntry(
                    id=uuid.uuid4(),
                    tenant_id=report.tenant_id,
                    user_id=report.user_id,
                    score_type="auto_report_ontime",
                    points=SCORE_VALUES["auto_report_ontime"],
                    reason=f"Отчёт подан вовремя за {week_start}—{week_end}",
                ))

        for entry in entries:
            session.add(entry)
        if entries:
            await session.commit()
            logger.info("Auto-scored %d report submissions", len(entries))
