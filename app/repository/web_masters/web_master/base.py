from abc import ABC

from sqlalchemy.ext.asyncio import AsyncSession


class WebMasterBaseRepository(ABC):
    async def get(
        self,
        db: AsyncSession,
    ):
        return "hello"
