import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.methods import DeleteWebhook

from app.repository.telegram.telegram_repo import TelegramRepository

from ...config.config import create_application_config
from .handlers import setup_handlers

logger = logging.getLogger(__name__)
config = create_application_config()


class TelegramService:
    def __init__(self, telegram_repo: TelegramRepository):
        self.telegram_repo = telegram_repo
        self.bot = Bot(token=config.telegram.token)
        self.dp = Dispatcher()
        setup_handlers(self.dp, self.telegram_repo)

    async def start_polling(self):
        while True:
            try:
                await self.bot(DeleteWebhook(drop_pending_updates=True))
                await self.dp.start_polling(self.bot, handle_signals=False)
            except Exception as e:
                logger.error(f"Polling stopped with error: {e}, restarting in 5 seconds...")
                await asyncio.sleep(5)

    async def send_message(self, chat_id: int, text: str):
        await self.bot.send_message(chat_id=chat_id, text=text)
