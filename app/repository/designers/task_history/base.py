from abc import ABC

from sqlalchemy.ext.asyncio import AsyncSession


class DesignerTaskHistoryBaseRepository(ABC):
    async def get(
        self,
        db: AsyncSession,
    ):
        return "Hello"
