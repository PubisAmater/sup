import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from arq.connections import RedisSettings
from sqlalchemy import select

from app.config import get_settings

logger = logging.getLogger(__name__)


async def process_meeting_analysis(ctx: dict, meeting_id: str) -> None:
    """Full meeting analysis pipeline: Claude AI → decisions + tasks in DB."""
    from app.database import async_session_factory
    from app.models.decision import Decision
    from app.models.meeting import Meeting
    from app.models.task import Task
    from app.models.user import User
    from app.services.claude import ClaudeService

    async with async_session_factory() as session:
        # 1. Load meeting
        result = await session.execute(
            select(Meeting).where(Meeting.id == uuid.UUID(meeting_id))
        )
        meeting = result.scalar_one_or_none()
        if not meeting or not meeting.transcript:
            logger.warning("Meeting %s not found or has no transcript", meeting_id)
            return

        meeting.processing_status = "processing"
        await session.commit()

        try:
            # 2. Build context: historical decisions (90 days)
            ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
            hist_result = await session.execute(
                select(Decision)
                .where(Decision.tenant_id == meeting.tenant_id)
                .where(Decision.created_at >= ninety_days_ago)
                .order_by(Decision.created_at.desc())
                .limit(100)
            )
            historical = hist_result.scalars().all()
            hist_text = "\n".join(
                f"[{d.created_at.strftime('%Y-%m-%d')}] {d.content}" for d in historical
            ) if historical else None

            # 3. Build context: open tasks
            open_result = await session.execute(
                select(Task)
                .where(Task.tenant_id == meeting.tenant_id)
                .where(Task.status.in_(["todo", "in_progress"]))
                .limit(50)
            )
            open_tasks = open_result.scalars().all()
            tasks_text = "\n".join(
                f"- {t.title} (статус: {t.status}, приоритет: {t.priority})" for t in open_tasks
            ) if open_tasks else None

            # 4. Call Claude
            claude = ClaudeService()
            analysis = await claude.analyze_meeting(
                transcript=meeting.transcript,
                historical_decisions=hist_text,
                open_tasks=tasks_text,
            )

            # 5. Save summary
            meeting.summary = analysis.summary
            meeting.processing_status = "completed"
            meeting.processing_error = None

            # 6. Create decisions in DB
            for dec_data in analysis.decisions:
                decision = Decision(
                    id=uuid.uuid4(),
                    tenant_id=meeting.tenant_id,
                    meeting_id=meeting.id,
                    content=dec_data.get("content", ""),
                    decided_by=meeting.organizer_id,
                    priority=dec_data.get("priority", "medium") or "medium",
                    status="active",
                )
                if dec_data.get("due_date_hint"):
                    try:
                        decision.due_date = date.fromisoformat(dec_data["due_date_hint"])
                    except (ValueError, TypeError):
                        pass
                session.add(decision)

            # 7. Create tasks in DB
            for task_data in analysis.tasks:
                task = Task(
                    id=uuid.uuid4(),
                    tenant_id=meeting.tenant_id,
                    title=task_data.get("title", "Без названия"),
                    description=task_data.get("description"),
                    assignee_id=meeting.organizer_id,  # default to organizer
                    meeting_id=meeting.id,
                    priority=task_data.get("priority", "medium") or "medium",
                    status="todo",
                )
                if task_data.get("due_date_hint"):
                    try:
                        task.due_date = date.fromisoformat(task_data["due_date_hint"])
                    except (ValueError, TypeError):
                        pass
                session.add(task)

            await session.commit()
            logger.info("Meeting %s analysis completed: %d decisions, %d tasks",
                        meeting_id, len(analysis.decisions), len(analysis.tasks))

        except Exception as e:
            logger.error("Meeting %s analysis failed: %s", meeting_id, e)
            meeting.processing_status = "failed"
            meeting.processing_error = str(e)[:2000]
            await session.commit()


async def sync_entity_to_notion(ctx: dict, entity_type: str, entity_id: str) -> None:
    """Sync a meeting, decision, or task to Notion."""
    from app.database import async_session_factory
    from app.models.decision import Decision
    from app.models.meeting import Meeting
    from app.models.task import Task
    from app.services.notion import NotionService

    notion = NotionService()

    async with async_session_factory() as session:
        try:
            if entity_type == "meeting":
                result = await session.execute(
                    select(Meeting).where(Meeting.id == uuid.UUID(entity_id))
                )
                meeting = result.scalar_one_or_none()
                if not meeting:
                    return
                page_id = await notion.sync_meeting(
                    meeting_id=meeting.id,
                    title=meeting.title,
                    status=meeting.status,
                    scheduled_at=meeting.scheduled_at.isoformat() if meeting.scheduled_at else None,
                    summary=meeting.summary,
                    existing_page_id=meeting.notion_page_id,
                )
                if page_id:
                    meeting.notion_page_id = page_id
                    await session.commit()

            elif entity_type == "decision":
                result = await session.execute(
                    select(Decision).where(Decision.id == uuid.UUID(entity_id))
                )
                decision = result.scalar_one_or_none()
                if not decision:
                    return
                page_id = await notion.sync_decision(
                    decision_id=decision.id,
                    content=decision.content,
                    status=decision.status,
                    priority=decision.priority,
                    due_date=decision.due_date.isoformat() if decision.due_date else None,
                    existing_page_id=decision.notion_page_id,
                )
                if page_id:
                    decision.notion_page_id = page_id
                    await session.commit()

            elif entity_type == "task":
                result = await session.execute(
                    select(Task).where(Task.id == uuid.UUID(entity_id))
                )
                task = result.scalar_one_or_none()
                if not task:
                    return
                page_id = await notion.sync_task(
                    task_id=task.id,
                    title=task.title,
                    status=task.status,
                    priority=task.priority,
                    due_date=task.due_date.isoformat() if task.due_date else None,
                    description=task.description,
                    existing_page_id=task.notion_page_id,
                )
                if page_id:
                    task.notion_page_id = page_id
                    await session.commit()

        except Exception as e:
            logger.error("Failed to sync %s %s to Notion: %s", entity_type, entity_id, e)


async def check_overdue_tasks(ctx: dict) -> None:
    """Find overdue tasks and notify assignees via Telegram."""
    from app.database import async_session_factory
    from app.models.task import Task
    from app.models.user import User
    from app.services.telegram_bot import TelegramBotService

    tg = TelegramBotService()
    today = date.today()

    async with async_session_factory() as session:
        result = await session.execute(
            select(Task, User)
            .join(User, Task.assignee_id == User.id)
            .where(Task.due_date < today)
            .where(Task.status.in_(["todo", "in_progress"]))
        )
        for task, user in result.all():
            if user.telegram_id:
                days_overdue = (today - task.due_date).days
                try:
                    await tg.send_message(
                        user.telegram_id,
                        f"⚠️ <b>Просроченная задача</b>\n\n"
                        f"📋 {task.title}\n"
                        f"📅 Срок: {task.due_date.isoformat()} "
                        f"(просрочена на {days_overdue} дн.)\n"
                        f"🔴 Приоритет: {task.priority}",
                    )
                except Exception as e:
                    logger.error("Failed to notify user %s: %s", user.id, e)


async def send_meeting_reminder(ctx: dict, meeting_id: str) -> None:
    """Send meeting reminder to all participants."""
    from app.database import async_session_factory
    from app.models.meeting import Meeting
    from app.models.meeting_participant import MeetingParticipant
    from app.models.user import User
    from app.services.telegram_bot import TelegramBotService

    tg = TelegramBotService()

    async with async_session_factory() as session:
        result = await session.execute(
            select(Meeting).where(Meeting.id == uuid.UUID(meeting_id))
        )
        meeting = result.scalar_one_or_none()
        if not meeting:
            return

        participants_result = await session.execute(
            select(User)
            .join(MeetingParticipant, MeetingParticipant.user_id == User.id)
            .where(MeetingParticipant.meeting_id == meeting.id)
        )
        for user in participants_result.scalars().all():
            if user.telegram_id:
                try:
                    scheduled = (
                        meeting.scheduled_at.strftime("%d.%m.%Y %H:%M")
                        if meeting.scheduled_at else "не указано"
                    )
                    await tg.send_message(
                        user.telegram_id,
                        f"🔔 <b>Напоминание о совещании</b>\n\n"
                        f"📋 {meeting.title}\n"
                        f"📅 {scheduled}\n"
                        f"⏱ {meeting.duration_minutes or '?'} мин.",
                    )
                except Exception as e:
                    logger.error("Failed to remind user %s: %s", user.id, e)


class WorkerSettings:
    functions = [
        process_meeting_analysis,
        sync_entity_to_notion,
        check_overdue_tasks,
        send_meeting_reminder,
    ]
    cron_jobs = [
        # Check overdue tasks daily at 9:00 AM
        # cron(check_overdue_tasks, hour=9, minute=0),
    ]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
