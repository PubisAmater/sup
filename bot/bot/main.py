import asyncio
import logging
import os

from aiogram import Bot, Dispatcher

from bot.handlers.notifications import router as notifications_router
from bot.handlers.start import router as start_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        return

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(start_router)
    dp.include_router(notifications_router)

    logger.info("Starting SUP bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
