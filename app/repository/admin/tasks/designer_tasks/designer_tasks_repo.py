import structlog
from fastapi import HTTPException
from sqlalchemy import delete, insert, select, update

from app.models import DesignerTask, DifficultyLevel, User
from app.repository.admin.tasks.designer_tasks.base import AdminDesignerTasksBaseRepository
from app.repository.designers.designer.utils import get_task
from app.repository.engine.database import DatabaseEngineRepository
from app.schemas.designers.lead_designer import (
    UpdateTaskDifficultyDesignerSchema,
)
from app.schemas.message import MessageSchema

logger = structlog.get_logger(__name__)


class AdminDesignerTaskRepository(AdminDesignerTasksBaseRepository, DatabaseEngineRepository):
    async def create_task_difficulty(self, name: str, points: int):
        async with self.session_maker() as db:
            if await db.scalar(
                select(DifficultyLevel).where(DifficultyLevel.name == name, DifficultyLevel.is_inactive.is_(False))
            ):
                raise HTTPException(status_code=409, detail=f"Difficulty level name '{name}' already exists")

            stmt = insert(DifficultyLevel).values(name=name, points=points).returning(DifficultyLevel)

            result = await db.execute(stmt)
            await db.commit()

            return result.scalar_one_or_none()

    async def get_all_task_difficulties(self):
        async with self.session_maker() as db:
            stmt = select(DifficultyLevel).where(~DifficultyLevel.is_inactive)
            result = await db.scalars(stmt)

            return result.all()

    async def update_task_difficulty(self, difficulty_id: int, task_difficulty: UpdateTaskDifficultyDesignerSchema):
        async with self.session_maker() as db:
            if await db.scalar(
                select(DifficultyLevel).where(
                    DifficultyLevel.name == task_difficulty.name, DifficultyLevel.id != difficulty_id
                )
            ):
                raise HTTPException(
                    status_code=409, detail=f"Difficulty level name '{task_difficulty.name}' already exists"
                )

            stmt = (
                update(DifficultyLevel)
                .where(DifficultyLevel.id == difficulty_id)
                .values(**task_difficulty.model_dump(exclude_unset=True))
                .returning(DifficultyLevel)
            )

            result = await db.execute(stmt)
            updated_difficulty = result.scalar_one_or_none()

            if not updated_difficulty:
                raise HTTPException(status_code=404, detail="Difficulty level not found")

            await db.commit()
            return updated_difficulty

    async def delete_task_difficulty(self, difficulty_id: int):
        async with self.session_maker() as db:
            stmt = (
                update(DifficultyLevel)
                .where(DifficultyLevel.id == difficulty_id)
                .values(is_inactive=True)
                .returning(DifficultyLevel.id)
            )
            result = await db.execute(stmt)
            updated_id = result.scalar_one_or_none()

            if not updated_id:
                raise HTTPException(status_code=404, detail="Difficulty level not found")

            await db.commit()

            return MessageSchema(message=f"Difficulty level with id {updated_id} was marked as inactive successfully")

    async def restore_task(self, task_id: int, user: User) -> DesignerTask:
        async with self.session_maker() as db:
            upd = (
                update(DesignerTask)
                .where(DesignerTask.id == task_id, DesignerTask.is_deleted.is_(True))
                .values(is_deleted=False)
            )
            if (await db.execute(upd)).rowcount == 0:
                raise HTTPException(404, "Deleted task not found")

            await db.commit()

        return await get_task(task_id=task_id, user=user, db=db)

    async def hard_delete_tasks(self, task_ids: list[int]) -> MessageSchema:
        async with self.session_maker() as db:
            query = (
                delete(DesignerTask)
                .where(DesignerTask.id.in_(task_ids), DesignerTask.is_deleted.is_(True))
                .returning(DesignerTask.id)
            )

            result = await db.execute(query)
            deleted = result.scalars().all()

            if not deleted:
                raise HTTPException(404, "Soft-deleted task(s) not found")

            await db.commit()
            return MessageSchema(message=f"Permanently deleted tasks: {', '.join(map(str, deleted))}")
