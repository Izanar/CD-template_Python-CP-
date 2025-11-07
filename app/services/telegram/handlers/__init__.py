from aiogram import Dispatcher

from app.repository.telegram.telegram_repo import TelegramRepository

from .me import register_me_handler
from .start import register_start_handler


def setup_handlers(dp: Dispatcher, telegram_repo: TelegramRepository):
    register_start_handler(dp, telegram_repo)
    register_me_handler(dp, telegram_repo)
