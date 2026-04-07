"""Автоматическое начисление баллов за выполнение задач и подачу отчётов.

Модуль реализует автоматическую часть системы геймификации (scoring):

- ``auto_score_tasks`` — ежедневно проверяет задачи, завершённые вчера,
  и начисляет баллы: положительные за выполнение в срок, отрицательные за просрочку;
- ``auto_score_reports`` — по понедельникам проверяет, кто подал еженедельный
  отчёт вовремя, и начисляет баллы за своевременную подачу.

Значения баллов настраиваются через константу ``SCORE_VALUES``.
Ручные бонусы/штрафы начисляются через API-эндпоинты ``/scores/bonus``
и ``/scores/penalty``.
"""

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
    """Автоначисление баллов за завершённые задачи (в срок vs с просрочкой).

    Ежедневно находит задачи, переведённые в статус ``done`` вчера,
    и начисляет баллы исполнителю:
    - ``+5`` за выполнение в срок (``auto_task_ontime``);
    - ``-3`` за выполнение с просрочкой (``auto_task_late``).

    Зачем: мотивирует сотрудников выполнять задачи вовремя через
    прозрачную систему баллов, отражающуюся в лидерборде.

    Args:
        ctx: Контекст arq-воркера.
    """
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
    """Автоначисление баллов за своевременную подачу еженедельных отчётов.

    Запускается только по понедельникам. Проверяет, кто подал отчёт
    за прошлую неделю (понедельник-воскресенье) до конца дня:
    - ``+3`` за подачу в срок (``auto_report_ontime``).

    Зачем: стимулирует сотрудников не забывать о еженедельной отчётности.
    Отсутствие отчёта пока не штрафуется (можно добавить при необходимости).

    Args:
        ctx: Контекст arq-воркера.
    """
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
