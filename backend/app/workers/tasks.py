import uuid

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings


async def process_meeting_summary(ctx: dict, meeting_id: str) -> None:
    """Process meeting transcript and generate AI summary."""
    from app.database import async_session_factory
    from app.models.meeting import Meeting
    from app.services.claude import ClaudeService

    async with async_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(Meeting).where(Meeting.id == uuid.UUID(meeting_id))
        )
        meeting = result.scalar_one_or_none()
        if not meeting or not meeting.transcript:
            return

        claude = ClaudeService()
        summary = await claude.summarize_meeting(meeting.transcript)
        meeting.summary = summary
        await session.commit()


async def sync_to_notion(ctx: dict, entity_type: str, entity_id: str) -> None:
    """Sync entity to Notion database."""
    from app.services.notion import NotionService

    notion = NotionService()
    # Implementation depends on Notion database structure
    pass


class WorkerSettings:
    functions = [process_meeting_summary, sync_to_notion]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
