import pytest_asyncio
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Creative


@pytest_asyncio.fixture
async def test_creative_with_data(engine, task_in_progress):
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as db_session:
        creative_data = {
            "task_id": task_in_progress["id"],
            "ad_name": "test_creative_api",
            "format": "vertical",
            "subtitles": True,
            "plashka": False,
            "approach": ["arrest", "cry", "check", "charges"],
        }

        result = await db_session.execute(insert(Creative).values(creative_data).returning(Creative))
        creative = result.scalar_one()
        await db_session.commit()

        result = await db_session.execute(select(Creative).where(Creative.id == creative.id))
        return result.scalar_one()


@pytest_asyncio.fixture
async def test_creative_minimal(engine, task_in_progress):
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as db_session:
        creative_data = {
            "task_id": task_in_progress["id"],
            "ad_name": "test_creative_minimal",
            "format": "horizontal",
            "subtitles": False,
            "plashka": True,
        }

        result = await db_session.execute(insert(Creative).values(creative_data).returning(Creative))
        creative = result.scalar_one()
        await db_session.commit()

        return creative


@pytest_asyncio.fixture
async def cleanup_test_creatives(engine):
    yield

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as db_session:
        await db_session.execute(delete(Creative).where(Creative.ad_name.like("test_creative%")))
        await db_session.commit()
