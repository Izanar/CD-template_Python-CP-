from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException

from app.dependecies.auth import AuthenticateUser
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.repository.designers.task_history.utils import handle_event_info
from app.schemas.enums.task_event import TaskEvent
from app.schemas.enums.task_status import WebMasterTaskStatus
from app.schemas.media_buyers.tasks.web_master_tasks import WebMasterTaskResponseSchema

web_master_router = APIRouter(
    prefix="/web_master",
    tags=["Web Master"],
)

logger = structlog.get_logger(__name__)


@web_master_router.post("/start_task/{task_id}", response_model=WebMasterTaskResponseSchema)
async def start_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticateUser()),
):
    if updated_task := await db_repo.web_master.update_task_status(
        task_id=task_id,
        task_status=WebMasterTaskStatus.IN_PROGRESS,
        current_user=current_user,
    ):
        logger.info(f"User {current_user.username} updated task {task_id} status to {WebMasterTaskStatus.IN_PROGRESS}")

        await db_repo.web_master_task_history.record_event(
            task_id=task_id,
            event=TaskEvent.STATUS_CHANGE.value,
            event_info=handle_event_info(
                event=TaskEvent.STATUS_CHANGE, new_status=WebMasterTaskStatus.IN_PROGRESS.value
            ),
            changed_by=current_user,
        )

        return updated_task

    return HTTPException(status_code=404, detail="Task not found")


@web_master_router.post("/mark_task_as_done/{task_id}", response_model=WebMasterTaskResponseSchema)
async def mark_task_as_done(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticateUser()),
):
    if updated_task := await db_repo.web_master.update_task_status(
        task_id=task_id,
        task_status=WebMasterTaskStatus.UNDER_TL_REVIEW,
        current_user=current_user,
    ):
        logger.info(
            f"User {current_user.username} updated task {task_id} status to {WebMasterTaskStatus.UNDER_TL_REVIEW}"
        )

        await db_repo.web_master_task_history.record_event(
            task_id=task_id,
            event=TaskEvent.STATUS_CHANGE.value,
            event_info=handle_event_info(
                event=TaskEvent.STATUS_CHANGE, new_status=WebMasterTaskStatus.UNDER_TL_REVIEW.value
            ),
            changed_by=current_user,
        )
        return updated_task

    return HTTPException(status_code=404, detail="Task not found")
