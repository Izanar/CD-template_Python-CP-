import uuid
from datetime import datetime, timezone
from typing import Sequence

import pytest_asyncio
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import DesignerTask, DesignerTaskDifficulty
from app.schemas.enums.task_status import DesignerTaskStatus


@pytest_asyncio.fixture
async def make_designer_tasks(engine, media_buyer_user):
    # tasks = await make_designer_tasks(status=DesignerTaskStatus.IN_PROGRESS, count=how many tasks you want)
    async def _builder(
        status: DesignerTaskStatus,
        count: int = 1,
        created_by_id: int | None = None,
        created_at: datetime | None = None,
        assigned_to_id: int | None = None,
        buyer_team_id: int | None = None,
    ) -> list[DesignerTask]:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            tasks = [
                DesignerTask(
                    title=f"auto_{uuid.uuid4().hex[:6]}",
                    description=f"auto_{uuid.uuid4().hex[:8]}",
                    task_status=status,
                    created_by_id=created_by_id or media_buyer_user["id"],
                    assigned_to_id=assigned_to_id,
                    created_at=created_at or datetime.now(timezone.utc),
                    completed_at=datetime.utcnow() if status is DesignerTaskStatus.COMPLETED else None,
                    buyer_team_id=buyer_team_id if buyer_team_id else None,
                )
                for _ in range(count)
            ]
            db.add_all(tasks)
            await db.commit()
            for task in tasks:
                await db.refresh(task)
            return tasks

    return _builder


@pytest_asyncio.fixture
async def make_tasks_with_points(
    engine,
    make_designer_tasks,
    new_difficulty,
):
    async def _builder(
        assigned_to_id: int, points: Sequence[int], created_by_id: int | None = None
    ) -> list[DesignerTask]:
        tasks = await make_designer_tasks(
            status=DesignerTaskStatus.COMPLETED,
            count=len(points),
            assigned_to_id=assigned_to_id,
            created_by_id=created_by_id,
        )

        point_to_id: dict[int, int] = {}
        for point in set(points):
            diff_dict = await new_difficulty(points=point)
            point_to_id[point] = diff_dict["id"]

        rows = [{"task_id": task.id, "difficulty_id": point_to_id[point]} for task, point in zip(tasks, points)]
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            await db.execute(insert(DesignerTaskDifficulty), rows)
            await db.commit()

        return tasks

    return _builder


@pytest_asyncio.fixture
async def make_tasks_with_operational(engine, make_designer_tasks):
    async def _builder(
        status: DesignerTaskStatus,
        assigned_to_id: int | None = None,
        count: int = 1,
        created_by_id: int | None = None,
    ) -> list[DesignerTask]:
        tasks = await make_designer_tasks(
            status=status,
            count=count,
            assigned_to_id=assigned_to_id,
            created_by_id=created_by_id,
        )

        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            for task in tasks:
                task.is_operational = True
                task.task_status = status
                task.title = f"o_{task.title}"
                db.add(task)
            await db.commit()
        return tasks

    return _builder
