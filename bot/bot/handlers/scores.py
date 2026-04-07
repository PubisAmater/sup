from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("bonus"))
async def cmd_bonus(message: Message):
    await message.answer(
        "<b>🏆 Начисление премии</b>\n\n"
        "Формат: <code>/bonus @username +10 Отличная работа</code>\n\n"
        "Или используйте веб-платформу для управления баллами.\n"
        "Доступно только для CEO.",
        parse_mode="HTML",
    )


@router.message(Command("penalty"))
async def cmd_penalty(message: Message):
    await message.answer(
        "<b>⚠️ Начисление штрафа</b>\n\n"
        "Формат: <code>/penalty @username -5 Просрочка задачи</code>\n\n"
        "Или используйте веб-платформу для управления баллами.\n"
        "Доступно только для CEO.",
        parse_mode="HTML",
    )


@router.message(Command("rating"))
async def cmd_rating(message: Message):
    await message.answer(
        "<b>📊 Рейтинг сотрудников</b>\n\n"
        "Рейтинг формируется автоматически:\n"
        "• +5 баллов за задачу в срок\n"
        "• -3 за просрочку\n"
        "• +3 за своевременный отчёт\n"
        "• Штрафы и премии CEO\n"
        "• Peer-review (раз в 2 недели)\n\n"
        "Полный рейтинг доступен в веб-платформе.",
        parse_mode="HTML",
    )
