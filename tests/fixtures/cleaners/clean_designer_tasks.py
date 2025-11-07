import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import DesignerTask


@pytest_asyncio.fixture
async def clean_designer_tasks(engine):
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        tasks = (await db.scalars(select(DesignerTask))).all()

        for task in tasks:
            await db.delete(task)

        await db.commit()
