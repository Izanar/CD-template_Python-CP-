from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query

from app.dependecies.auth import AuthenticateAdmin, AuthenticatedDesignerTasksRoles
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.designers.designer import DesignerTaskDifficultiesSchema
from app.schemas.designers.lead_designer import (
    CreateTaskDifficultyDesignerSchema,
    TaskDifficultyDesignerResponseSchema,
    UpdateTaskDifficultyDesignerSchema,
)
from app.schemas.media_buyers.tasks.designer_tasks import (
    DesignerTaskResponseSchemaWithCreator,
)
from app.schemas.message import MessageSchema

admin_designer_tasks_router = APIRouter(
    prefix="/admin/designer/tasks",
    tags=["Admin"],
)

logger = structlog.get_logger()


@admin_designer_tasks_router.post("/create_difficulty", response_model=TaskDifficultyDesignerResponseSchema)
async def create_designer_task_difficulty(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    data: CreateTaskDifficultyDesignerSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_designer_task.create_task_difficulty(name=data.name, points=data.points)


@admin_designer_tasks_router.get("/view_difficulties", response_model=list[DesignerTaskDifficultiesSchema])
async def view_task_difficulties(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticatedDesignerTasksRoles()),
) -> list[DesignerTaskDifficultiesSchema]:
    return await db_repo.admin_designer_task.get_all_task_difficulties()


@admin_designer_tasks_router.patch("/update_difficulty", response_model=TaskDifficultyDesignerResponseSchema)
async def update_designer_task_difficulty(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    data: UpdateTaskDifficultyDesignerSchema,
    difficulty_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_designer_task.update_task_difficulty(difficulty_id=difficulty_id, task_difficulty=data)


@admin_designer_tasks_router.delete("/remove_difficulty", response_model=MessageSchema)
async def delete_designer_task_difficulty(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    difficulty_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_designer_task.delete_task_difficulty(difficulty_id=difficulty_id)


@admin_designer_tasks_router.post(
    "/restore/{task_id}",
    response_model=DesignerTaskResponseSchemaWithCreator,
    summary="Restore deleted task",
)
async def restore_designer_task(
    task_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_designer_task.restore_task(task_id, user=current_user)


@admin_designer_tasks_router.delete(
    "/hard_remove",
    response_model=MessageSchema,
    summary="Hard-delete previously soft-deleted tasks",
)
async def hard_remove_designer_tasks(
    task_id: Annotated[list[int], Query(..., description="Repeat to delete several tasks")],
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_designer_task.hard_delete_tasks(task_id)
