import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


@router.message(Command("report"))
async def cmd_report(message: Message):
    await message.answer(
        "<b>📊 Еженедельный отчёт</b>\n\n"
        "Для подачи отчёта перейдите в веб-платформу:\n"
        f"<a href='{FRONTEND_URL}/dashboard/reports/new'>Подать отчёт</a>\n\n"
        "В отчёте укажите:\n"
        "• Выполненные задачи с итогами\n"
        "• Ключевые метрики\n"
        "• Запросы управленческих решений\n\n"
        "После подачи CEO получит отчёт в Telegram\n"
        "с аудио-саммари через SpeechKit.",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
