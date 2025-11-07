from typing import Annotated

import structlog
from fastapi import APIRouter, Depends

from app.dependecies.auth import AuthenticateAdmin, AuthenticateWebMasterTasksRoles
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.lead_web_master import (
    CreateTaskDifficultyWebMasterSchema,
    TaskDifficultyWebMasterResponseSchema,
    UpdateTaskDifficultyWebMasterSchema,
)
from app.schemas.media_buyers.tasks.web_master_tasks import (
    WebMasterTaskTypeCreateSchema,
    WebMasterTaskTypeResponseSchema,
)
from app.schemas.message import MessageSchema
from app.schemas.web_masters.web_master import WebMasterTaskDifficultiesSchema

admin_web_master_tasks_router = APIRouter(
    prefix="/admin/web_master/tasks",
    tags=["Admin"],
)

logger = structlog.get_logger()


@admin_web_master_tasks_router.post("/create_difficulty", response_model=TaskDifficultyWebMasterResponseSchema)
async def create_web_master_task_difficulty(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    data: CreateTaskDifficultyWebMasterSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_web_master_task.create_task_difficulty(name=data.name, points=data.points)


@admin_web_master_tasks_router.get("/view_difficulties", response_model=list[TaskDifficultyWebMasterResponseSchema])
async def view_task_difficulties(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateWebMasterTasksRoles()),
) -> list[WebMasterTaskDifficultiesSchema]:
    return await db_repo.admin_web_master_task.get_all_task_difficulties()


@admin_web_master_tasks_router.patch("/update_difficulty", response_model=TaskDifficultyWebMasterResponseSchema)
async def update_web_master_task_difficulty(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    data: UpdateTaskDifficultyWebMasterSchema,
    difficulty_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_web_master_task.update_task_difficulty(difficulty_id=difficulty_id, task_difficulty=data)


@admin_web_master_tasks_router.delete("/remove_difficulty", response_model=MessageSchema)
async def delete_web_master_task_difficulty(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    difficulty_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_web_master_task.delete_task_difficulty(difficulty_id=difficulty_id)


@admin_web_master_tasks_router.post(
    "/create_type",
    response_model=WebMasterTaskTypeResponseSchema,
)
async def create_web_master_task_type(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_type: WebMasterTaskTypeCreateSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_web_master_task.create_task_type(task_type=task_type)


@admin_web_master_tasks_router.get(
    "/task_types",
    response_model=list[WebMasterTaskTypeResponseSchema],
)
async def get_web_master_task_types(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateWebMasterTasksRoles()),
):
    return await db_repo.admin_web_master_task.get_all_task_types()


@admin_web_master_tasks_router.delete(
    "/remove_type/{task_type_id}",
    response_model=MessageSchema,
)
async def delete_web_master_task_type(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_type_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_web_master_task.delete_task_type(
        task_type_id=task_type_id,
    )
