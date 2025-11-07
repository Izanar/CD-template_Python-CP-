from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models import Designer, MediaBuyer, User
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.telegram.base import TelegramBaseRepository


class TelegramRepository(TelegramBaseRepository, DatabaseEngineRepository):
    async def set_telegram_token(self, user_id: int) -> str:
        async with self.session_maker() as db:
            token = str(uuid4())
            stmt = update(User).where(User.id == user_id).values(telegram_token=token)
            await db.execute(stmt)
            await db.commit()
            return token

    async def get_user_by_token(self, token: str) -> User | None:
        async with self.session_maker() as db:
            stmt = select(User).where(User.telegram_token == token)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

    async def update_telegram_chat_id(self, user_id: int, chat_id: int):
        async with self.session_maker() as db:
            stmt = update(User).where(User.id == user_id).values(telegram_chat_id=chat_id, telegram_token=None)
            await db.execute(stmt)
            await db.commit()

    async def get_user_by_chat_id(self, chat_id: int) -> User | None:
        async with self.session_maker() as db:
            stmt = (
                select(User)
                .where(User.telegram_chat_id == chat_id)
                .options(
                    selectinload(User.designer).selectinload(Designer.teams),
                    selectinload(User.media_buyer).selectinload(MediaBuyer.teams),
                )
            )
            result = await db.execute(stmt)
            return result.unique().scalar_one_or_none()

    async def get_chat_id_by_user_id(self, user_id: int) -> int | None:
        async with self.session_maker() as db:
            stmt = select(User.telegram_chat_id).where(User.id == user_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

    async def logout_user(self, user_id: int) -> None:
        async with self.session_maker() as db:
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            if user.telegram_chat_id is None and user.telegram_token is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You are not registered",
                )

            stmt = update(User).where(User.id == user_id).values(telegram_chat_id=None, telegram_token=None)
            await db.execute(stmt)
            await db.commit()

    async def clear_telegram_token(self, user_id: int) -> None:
        async with self.session_maker() as db:
            stmt = update(User).where(User.id == user_id).values(telegram_token=None)
            await db.execute(stmt)
            await db.commit()
