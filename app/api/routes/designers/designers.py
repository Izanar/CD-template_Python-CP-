from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException

from app.dependecies.auth import AuthenticatedDesignerTasksRoles
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.repository.media_buyers.tasks.utils import check_task_status
from app.schemas.enums.task_event import TaskEvent
from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.media_buyers.tasks.designer_tasks import DesignerTaskResponseSchema

designer_router = APIRouter(
    prefix="/designer",
    tags=["Designer"],
)
logger = structlog.get_logger(__name__)


@designer_router.post("/start_task/{task_id}", response_model=DesignerTaskResponseSchema)
async def start_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticatedDesignerTasksRoles()),
):
    existing_task = await db_repo.designer_task.get_task(task_id=task_id, user=current_user)
    await check_task_status(
        task=existing_task,
        allowed_statuses=[
            DesignerTaskStatus.IN_PROGRESS,
            DesignerTaskStatus.WAITING_TO_START,
            DesignerTaskStatus.REQUESTED_CHANGES,
        ],
        detail=f"You cannot change this task in its current status ({existing_task.task_status.value}).",
    )
    if updated_task := await db_repo.designer.update_task_status(
        task_id=task_id,
        task_status=DesignerTaskStatus.IN_PROGRESS,
        current_user=current_user,
    ):
        logger.info(f"User {current_user.username} updated task {task_id} status to {DesignerTaskStatus.IN_PROGRESS}")

        await db_repo.designer_task_history.record_event(
            task_id=task_id,
            event=TaskEvent.STATUS.value,
            event_info=updated_task.task_status.value,
            description=f"Task started by {current_user.username}",
            changed_by=current_user,
        )

        return updated_task

    return HTTPException(status_code=404, detail="Task not found")


@designer_router.post("/mark_task_as_done/{task_id}", response_model=DesignerTaskResponseSchema)
async def mark_task_as_done(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticatedDesignerTasksRoles()),
):
    existing_task = await db_repo.designer_task.get_task(task_id=task_id, user=current_user)
    await check_task_status(
        task=existing_task,
        required_status=DesignerTaskStatus.IN_PROGRESS,
        detail=f"You cannot change this task in its current status ({existing_task.task_status.value}).",
    )
    if updated_task := await db_repo.designer.update_task_status(
        task_id=task_id,
        task_status=DesignerTaskStatus.UNDER_TL_REVIEW,
        current_user=current_user,
    ):
        logger.info(
            f"User {current_user.username} updated task {task_id} status to {DesignerTaskStatus.UNDER_TL_REVIEW}"
        )

        await db_repo.designer_task_history.record_event(
            task_id=task_id,
            event=TaskEvent.STATUS.value,
            event_info=updated_task.task_status.value,
            description=f"Task marked as done by {current_user.username}",
            changed_by=current_user,
        )

        return updated_task

    return HTTPException(status_code=404, detail="Task not found")
