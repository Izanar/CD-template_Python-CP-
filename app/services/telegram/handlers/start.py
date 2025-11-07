from aiogram import Dispatcher, types
from aiogram.filters import CommandStart

from app.repository.telegram.telegram_repo import TelegramRepository


def register_start_handler(dp: Dispatcher, telegram_repo: TelegramRepository):
    @dp.message(CommandStart())
    async def start_command(message: types.Message):
        chat_id = message.chat.id

        if await telegram_repo.get_user_by_chat_id(chat_id):
            await message.answer("You are already registered! Use /me to view your profile.")
            return

        parts = message.text.split(maxsplit=1)
        token = parts[1] if len(parts) > 1 else None
        if not token:
            await message.answer("Please use /start with token to register.")
            return

        user = await telegram_repo.get_user_by_token(token)
        if not user:
            await message.answer("Invalid registration token.")
            return
        if user.telegram_chat_id:
            await telegram_repo.clear_telegram_token(user.id)
            await message.answer("You are already registered! Use /me to view your profile.")
            return

        await telegram_repo.update_telegram_chat_id(user.id, chat_id)

        await message.answer("You have been successfully registered! Use /me to view your profile.")
