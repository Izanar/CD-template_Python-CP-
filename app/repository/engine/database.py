from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
)

from app.repository.engine.base import Repository


class DatabaseEngineRepository(Repository):
    def __init__(self, session_maker: async_sessionmaker) -> None:
        self.session_maker = session_maker
