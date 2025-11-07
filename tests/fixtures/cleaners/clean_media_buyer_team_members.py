import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker


@pytest_asyncio.fixture(autouse=True)
async def clean_media_buyer_team_members(engine):
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        await db.execute(text("DELETE FROM media_buyers_team_members"))
        await db.commit()
