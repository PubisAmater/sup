"""Доставка еженедельных отчётов CEO в Telegram и генерация аудио-саммари через SpeechKit.

Модуль содержит два arq-воркера:

- ``deliver_report_to_ceo`` — форматирует отчёт сотрудника в Telegram-сообщения
  (блоки: заголовок, выполненные задачи, метрики, запросы) и отправляет
  всем пользователям с ролью ``ceo`` в тенанте;
- ``generate_audio_summary`` — генерирует аудио-версию отчёта через Yandex SpeechKit
  и отправляет голосовое сообщение CEO в Telegram.

Зачем: CEO может ознакомиться с отчётами «на ходу» — прочитать в Telegram
или прослушать аудио-саммари, не заходя в веб-интерфейс.
"""

import logging
import uuid

from sqlalchemy import select

from app.config import get_settings

logger = logging.getLogger(__name__)


async def deliver_report_to_ceo(ctx: dict, report_id: str) -> None:
    """Форматирует еженедельный отчёт в Telegram-блоки и доставляет CEO.

    Этапы:
    1. Загрузка отчёта и автора из БД;
    2. Поиск всех пользователей с ролью ``ceo`` в том же тенанте;
    3. Формирование блоков сообщений (заголовок, задачи, метрики, запросы);
    4. Последовательная отправка блоков каждому CEO через Telegram Bot API.

    Зачем: CEO получает отчёты в реальном времени без необходимости
    заходить в веб-интерфейс. Блочная отправка позволяет Telegram
    корректно отображать длинные тексты.

    Args:
        ctx: Контекст arq-воркера.
        report_id: UUID отчёта в строковом формате.
    """
    from app.database import async_session_factory
    from app.models.user import User
    from app.models.weekly_report import WeeklyReport
    from app.services.telegram_bot import TelegramBotService

    tg = TelegramBotService()

    async with async_session_factory() as session:
        result = await session.execute(
            select(WeeklyReport).where(WeeklyReport.id == uuid.UUID(report_id))
        )
        report = result.scalar_one_or_none()
        if not report:
            return

        # Get report author
        author_result = await session.execute(
            select(User).where(User.id == report.user_id)
        )
        author = author_result.scalar_one_or_none()
        author_name = f"{author.first_name} {author.last_name or ''}" if author else "Неизвестный"

        # Get CEO users
        ceo_result = await session.execute(
            select(User)
            .where(User.tenant_id == report.tenant_id)
            .where(User.role == "ceo")
        )
        ceo_users = ceo_result.scalars().all()

        # Format report blocks
        blocks = [
            f"📊 <b>Еженедельный отчёт</b>\n"
            f"👤 {author_name}\n"
            f"📅 {report.period_start.isoformat()} — {report.period_end.isoformat()}\n",
        ]

        if report.completed_tasks:
            blocks.append(f"✅ <b>Выполненные задачи:</b>\n{report.completed_tasks}")

        if report.metrics_json:
            blocks.append(f"📈 <b>Метрики:</b>\n{report.metrics_json}")

        if report.requests:
            blocks.append(f"❓ <b>Запросы управленческих решений:</b>\n{report.requests}")

        # Send blocks to each CEO
        for ceo in ceo_users:
            if ceo.telegram_id:
                for block in blocks:
                    try:
                        await tg.send_message(ceo.telegram_id, block)
                    except Exception as e:
                        logger.error("Failed to send report block to CEO %s: %s", ceo.id, e)

        logger.info("Report %s delivered to %d CEO users", report_id, len(ceo_users))


async def generate_audio_summary(ctx: dict, report_id: str) -> None:
    """Генерирует аудио-саммари отчёта через Yandex SpeechKit и отправляет CEO.

    Этапы:
    1. Загрузка отчёта и автора из БД;
    2. Формирование текста для озвучки (автор, период, задачи, запросы);
    3. Синтез речи через SpeechKit (text-to-speech);
    4. Отправка аудиофайла всем CEO в Telegram.

    Зачем: CEO может прослушать краткое содержание отчёта в аудиоформате —
    удобно при поездках или когда нет возможности читать текст.

    Args:
        ctx: Контекст arq-воркера.
        report_id: UUID отчёта в строковом формате.
    """
    from app.database import async_session_factory
    from app.models.user import User
    from app.models.weekly_report import WeeklyReport
    from app.services.speechkit import SpeechKitService
    from app.services.telegram_bot import TelegramBotService

    async with async_session_factory() as session:
        result = await session.execute(
            select(WeeklyReport).where(WeeklyReport.id == uuid.UUID(report_id))
        )
        report = result.scalar_one_or_none()
        if not report:
            return

        # Build text for TTS
        author_result = await session.execute(
            select(User).where(User.id == report.user_id)
        )
        author = author_result.scalar_one_or_none()
        author_name = f"{author.first_name} {author.last_name or ''}" if author else "сотрудник"

        text_parts = [
            f"Отчёт от {author_name} за период "
            f"с {report.period_start.isoformat()} по {report.period_end.isoformat()}.",
        ]
        if report.completed_tasks:
            text_parts.append(f"Выполненные задачи: {report.completed_tasks[:500]}")
        if report.requests:
            text_parts.append(f"Запросы: {report.requests[:300]}")

        summary_text = " ".join(text_parts)

        try:
            speechkit = SpeechKitService()
            audio = await speechkit.text_to_speech(summary_text)

            # Send audio to CEO
            tg = TelegramBotService()
            ceo_result = await session.execute(
                select(User)
                .where(User.tenant_id == report.tenant_id)
                .where(User.role == "ceo")
            )
            for ceo in ceo_result.scalars().all():
                if ceo.telegram_id:
                    await tg.send_audio(
                        ceo.telegram_id,
                        audio,
                        caption=f"🔊 Аудио-саммари: {author_name}",
                    )

            logger.info("Audio summary generated and sent for report %s", report_id)
        except Exception as e:
            logger.error("Audio summary generation failed for report %s: %s", report_id, e)
