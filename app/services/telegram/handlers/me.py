from aiogram import Dispatcher, types
from aiogram.filters import Command

from app.repository.telegram.telegram_repo import TelegramRepository


def register_me_handler(dp: Dispatcher, telegram_repo: TelegramRepository):
    @dp.message(Command("me"))
    async def me_command(message: types.Message):
        chat_id = message.chat.id
        user = await telegram_repo.get_user_by_chat_id(chat_id)

        if not user:
            await message.answer("You are not registered. Use /start with token to register.")
            return

        team_name = user.team.team_name if user.team else "No team"
        response = f"Username: {user.username}\nRole: {user.role.value}\nTeam: {team_name}"

        await message.answer(response)
