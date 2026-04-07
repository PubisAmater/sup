import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть СУП", url=frontend_url)],
        ]
    )
    await message.answer(
        "Добро пожаловать в <b>СУП</b> — Систему Управления Персоналом!\n\n"
        "Нажмите кнопку ниже, чтобы войти в платформу.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>Доступные команды:</b>\n\n"
        "/start — Начать работу\n"
        "/help — Список команд\n"
        "/status — Статус задач\n"
        "/report — Еженедельный отчёт",
        parse_mode="HTML",
    )


@router.message(Command("status"))
async def cmd_status(message: Message):
    await message.answer(
        "Функция в разработке. Скоро здесь будет сводка по вашим задачам.",
        parse_mode="HTML",
    )
