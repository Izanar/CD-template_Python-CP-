import asyncio
import os
import re

import pytest
import pytest_asyncio
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.dependecies.stub import DatabaseRepositoryStub
from app.models import Base
from app.repository.database.base import DatabaseRepository

SHARED_DSN = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"
os.environ["DATABASE_URL"] = SHARED_DSN


@pytest.fixture(scope="session")
def engine() -> AsyncEngine:
    eng = create_async_engine(
        SHARED_DSN,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(eng.sync_engine, "connect")
    def _enable_sqlite_fks(dbapi_conn, _) -> None:
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

        def sqlite_regexp_replace(*args):
            if len(args) == 3:
                expr, pattern, repl = args
                flags = ""
            elif len(args) == 4:
                expr, pattern, repl, flags = args
            else:
                raise ValueError("regexp_replace expects 3 or 4 arguments")

            if expr is None:
                return None

            re_flags = re.IGNORECASE if "i" in flags else 0
            return re.sub(pattern, repl, str(expr), flags=re_flags)

        dbapi_conn.create_function("regexp_replace", -1, sqlite_regexp_replace)

        def sqlite_substring_regex(expr, pattern):
            if expr is None:
                return None
            m = re.search(pattern, str(expr))
            return m.group(0) if m else None

        dbapi_conn.create_function("substring", 2, sqlite_substring_regex)

        def split_part(val, delim, idx) -> str | None:
            if val is None:
                return None
            parts = str(val).split(delim)
            i = int(idx) - 1
            return parts[i] if 0 <= i < len(parts) else None

        dbapi_conn.create_function("split_part", 3, split_part)

        def reverse(val) -> str | None:
            if val is None:
                return None
            return str(val)[::-1]

        dbapi_conn.create_function("reverse", 1, reverse)

    async def _prepare() -> None:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_prepare())
    return eng


@pytest_asyncio.fixture(scope="session")
async def app(engine: AsyncEngine):
    from app.main import create_app

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    db_repo = DatabaseRepository.create(session_maker)

    fastapi_app = create_app(configure_logging=False)
    fastapi_app.dependency_overrides[DatabaseRepositoryStub] = lambda: db_repo
    return fastapi_app


@pytest_asyncio.fixture(scope="session")
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
