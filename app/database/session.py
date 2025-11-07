from dataclasses import dataclass

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.config import ConfigDTO


@dataclass(frozen=True, slots=True)
class Database:
    engine: AsyncEngine
    async_session_maker: async_sessionmaker[AsyncSession]

    @classmethod
    def create(
        cls,
        dsn: str,
        pool_size: int,
        max_overflow: int,
        pool_recycle: int,
        pool_timeout: int,
        query_cache_size: int = 500,
    ) -> "Database":
        connection_args = {
            "prepare_threshold": None,
        }

        db_engine: AsyncEngine = create_async_engine(
            dsn,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            pool_timeout=pool_timeout,
            connect_args=connection_args,
            query_cache_size=query_cache_size,
        )
        async_session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False
        )

        return cls(
            engine=db_engine,
            async_session_maker=async_session_maker,
        )


def configure_database_engine(config: ConfigDTO):
    return Database.create(
        dsn=config.postgres.dsn,
        pool_size=config.postgres.pool_size,
        max_overflow=config.postgres.pool_max_overflow,
        pool_recycle=config.postgres.pool_recycle,
        pool_timeout=config.postgres.pool_timeout,
    )


def setup_database(config: ConfigDTO):
    return configure_database_engine(config=config)
