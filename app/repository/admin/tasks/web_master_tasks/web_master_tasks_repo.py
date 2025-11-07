import structlog
from fastapi import HTTPException
from sqlalchemy import delete, exists, insert, select, update

from app.models import WebMasterDifficultyLevel, WebMasterTask, WebMasterTaskType
from app.repository.admin.tasks.web_master_tasks.base import AdminWebMasterTasksBaseRepository
from app.repository.engine.database import DatabaseEngineRepository
from app.schemas.lead_web_master import UpdateTaskDifficultyWebMasterSchema
from app.schemas.media_buyers.tasks.web_master_tasks import (
    WebMasterTaskTypeCreateSchema,
    WebMasterTaskTypeResponseSchema,
)
from app.schemas.message import MessageSchema

logger = structlog.get_logger(__name__)


# TODO: Add methods in the feature (create_task_difficulty, update_task_difficulty, delete_task_difficulty)


class AdminWebMasterTaskRepository(AdminWebMasterTasksBaseRepository, DatabaseEngineRepository):
    async def create_task_type(self, task_type: WebMasterTaskTypeCreateSchema) -> WebMasterTaskTypeResponseSchema:
        async with self.session_maker() as db:
            if await db.scalar(select(WebMasterTaskType).where(WebMasterTaskType.name == task_type.name)):
                raise HTTPException(status_code=409, detail=f"Task type name '{task_type.name}' already exists")

            stmt = insert(WebMasterTaskType).values(name=task_type.name).returning(WebMasterTaskType)

            result = await db.execute(stmt)
            await db.commit()

            return result.scalar()

    async def get_all_task_types(self):
        async with self.session_maker() as db:
            result = await db.scalars(select(WebMasterTaskType))
            return result.all()

    async def delete_task_type(self, task_type_id: int) -> MessageSchema:
        async with self.session_maker() as db:
            task_exists = await db.scalar(select(exists().where(WebMasterTask.task_type_id == task_type_id)))

            if task_exists:
                raise HTTPException(status_code=409, detail="Cannot delete task type because it is in use.")

            stmt = delete(WebMasterTaskType).where(WebMasterTaskType.id == task_type_id).returning(WebMasterTaskType.id)

            result = await db.execute(stmt)

            deleted_task_type = result.scalar_one_or_none()

            if not deleted_task_type:
                raise HTTPException(status_code=404, detail="Task type not found")

            await db.commit()

            return MessageSchema(message=f"Task type {deleted_task_type} was deleted successfully")

    async def create_task_difficulty(self, name: str, points: int):
        async with self.session_maker() as db:
            if await db.scalar(select(WebMasterDifficultyLevel).where(WebMasterDifficultyLevel.name == name)):
                raise HTTPException(status_code=409, detail=f"Difficulty level name '{name}' already exists")

            stmt = insert(WebMasterDifficultyLevel).values(name=name, points=points).returning(WebMasterDifficultyLevel)

            result = await db.execute(stmt)
            await db.commit()

            return result.scalar_one_or_none()

    async def get_all_task_difficulties(self):
        async with self.session_maker() as db:
            stmt = select(WebMasterDifficultyLevel)
            result = await db.scalars(stmt)

            return result.all()

    async def update_task_difficulty(self, difficulty_id: int, task_difficulty: UpdateTaskDifficultyWebMasterSchema):
        async with self.session_maker() as db:
            if await db.scalar(
                select(WebMasterDifficultyLevel).where(
                    WebMasterDifficultyLevel.name == task_difficulty.name, WebMasterDifficultyLevel.id != difficulty_id
                )
            ):
                raise HTTPException(
                    status_code=409, detail=f"Difficulty level name '{task_difficulty.name}' already exists"
                )

            stmt = (
                update(WebMasterDifficultyLevel)
                .where(WebMasterDifficultyLevel.id == difficulty_id)
                .values(**task_difficulty.model_dump(exclude_unset=True))
                .returning(WebMasterDifficultyLevel)
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
                delete(WebMasterDifficultyLevel)
                .where(WebMasterDifficultyLevel.id == difficulty_id)
                .returning(WebMasterDifficultyLevel.id)
            )
            result = await db.execute(stmt)
            deleted_id = result.scalar_one_or_none()

            if not deleted_id:
                raise HTTPException(status_code=404, detail="Difficulty level not found")

            await db.commit()

            return MessageSchema(message=f"Difficulty level with id {deleted_id} was deleted successfully")
