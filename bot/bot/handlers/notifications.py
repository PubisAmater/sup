import os

import httpx
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


async def _api_get(endpoint: str, telegram_id: int) -> dict | None:
    """Call backend API. In production this would use a service token."""
    try:
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10) as client:
            response = await client.get(endpoint)
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None


@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    # In production: authenticate via bot token and get user's tasks
    await message.answer(
        "<b>Ваши задачи:</b>\n\n"
        "Для просмотра задач откройте веб-платформу.\n"
        "Функция просмотра задач через бот будет доступна в ближайшем обновлении.\n\n"
        "Вы можете получать уведомления о:\n"
        "• Просроченных задачах\n"
        "• Новых назначенных задачах\n"
        "• Решениях с совещаний",
        parse_mode="HTML",
    )


@router.message(Command("meetings"))
async def cmd_meetings(message: Message):
    await message.answer(
        "<b>Совещания:</b>\n\n"
        "Для просмотра совещаний откройте веб-платформу.\n"
        "Функция просмотра через бот будет доступна в ближайшем обновлении.\n\n"
        "Вы будете получать уведомления:\n"
        "• Напоминание за 30 минут до совещания\n"
        "• Результаты обработки (решения, задачи)\n"
        "• Аудио-саммари (скоро)",
        parse_mode="HTML",
    )


@router.message(Command("report"))
async def cmd_report(message: Message):
    await message.answer(
        "<b>Еженедельный отчёт:</b>\n\n"
        "Функция подачи отчётов будет доступна в Этапе 3.\n"
        "Топ-менеджеры смогут подавать отчёты через веб-форму,\n"
        "а CEO получит сводку прямо в Telegram с аудио-саммари.",
        parse_mode="HTML",
    )
