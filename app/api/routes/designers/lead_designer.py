from typing import Annotated, List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependecies.auth import AuthenticateDesignerOrLead, AuthenticateLeadDesigner
from app.dependecies.stub import DatabaseRepositoryStub
from app.dependecies.telegram import get_telegram_service
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.repository.media_buyers.tasks.utils import check_task_status
from app.repository.telegram.utils import notify_creator_task_ready
from app.schemas.designers.lead_designer import (
    DesignerLoadTaskSchema,
    DesignerShortResponseSchema,
)
from app.schemas.enums.task_event import TaskAction, TaskEvent
from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.media_buyers.tasks.designer_tasks import (
    CreateOperationDesignerTaskSchema,
    DesignerPointsRequest,
    DesignerTaskResponseSchema,
    DesignerUserPointsResponse,
    UpdateDesignerTaskSchema,
)
from app.services.telegram import TelegramService

logger = structlog.get_logger()

lead_designer_router = APIRouter(
    prefix="/lead_designer",
    tags=["Lead Designer"],
)


@lead_designer_router.post("/task/{task_id}/approve", response_model=DesignerTaskResponseSchema)
async def approve_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    telegram_service: Annotated[TelegramService, Depends(get_telegram_service)],
    current_user: User = Depends(AuthenticateLeadDesigner()),
):
    existing_task = await db_repo.designer_task.get_task(task_id=task_id, user=current_user)
    await check_task_status(
        task=existing_task,
        required_status=DesignerTaskStatus.UNDER_TL_REVIEW,
        detail=f"You cannot change this task in its current status ({existing_task.task_status.value}).",
    )
    if updated_task := await db_repo.designer.update_task_status(
        task_id=task_id,
        task_status=DesignerTaskStatus.COMPLETED
        if existing_task.is_operational
        else DesignerTaskStatus.UNDER_BUYER_REVIEW,
        current_user=current_user,
    ):
        logger.info(
            f"User {current_user.username} updated task {task_id} status to {DesignerTaskStatus.UNDER_BUYER_REVIEW}"
        )

        await db_repo.designer_task_history.record_event(
            task_id=task_id,
            event=TaskEvent.STATUS.value,
            event_info=updated_task.task_status.value,
            description=f"Task approved by {current_user.username}",
            changed_by=current_user,
        )
        if updated_task.task_status == DesignerTaskStatus.UNDER_BUYER_REVIEW:
            await notify_creator_task_ready(db_repo, telegram_service, updated_task)

        return updated_task

    return HTTPException(status_code=404, detail="Task not found")


@lead_designer_router.post("/task/{task_id}/request_changes", response_model=DesignerTaskResponseSchema)
async def request_changes_on_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticateLeadDesigner()),
):
    existing_task = await db_repo.designer_task.get_task(task_id=task_id, user=current_user)
    await check_task_status(
        task=existing_task,
        required_status=DesignerTaskStatus.UNDER_TL_REVIEW,
        detail=f"You cannot change this task in its current status ({existing_task.task_status.value}).",
    )
    if updated_task := await db_repo.designer.update_task_status(
        task_id=task_id,
        task_status=DesignerTaskStatus.REQUESTED_CHANGES,
        current_user=current_user,
    ):
        logger.info(
            f"User {current_user.username} updated task {task_id} status to {DesignerTaskStatus.REQUESTED_CHANGES}"
        )

        await db_repo.designer_task_history.record_event(
            task_id=task_id,
            event=TaskEvent.STATUS.value,
            event_info=updated_task.task_status.value,
            description=f"Changes requested by {current_user.username}",
            changed_by=current_user,
        )

        return updated_task

    return HTTPException(status_code=404, detail="Task not found")


@lead_designer_router.patch("/task/update", response_model=DesignerTaskResponseSchema)
async def update_designer_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_info: UpdateDesignerTaskSchema,
    current_user: User = Depends(AuthenticateDesignerOrLead()),
):
    task = await db_repo.lead_designer.update_designer_task(task_info=task_info, user=current_user)
    await db_repo.designer_task_history.record_event(
        task_id=task.id,
        event=TaskEvent.TASK.value,
        event_info=TaskAction.UPDATED.value,
        description=f"Task updated by {current_user.username}",
        changed_by=current_user,
    )

    await db_repo.designer_task_history.record_event(
        task_id=task.id,
        event=TaskEvent.STATUS.value,
        event_info=task.task_status.value,
        description=f"Task status changed to {task.task_status.value} by {current_user.username}",
        changed_by=current_user,
    )
    return task


@lead_designer_router.get("/designer_points", response_model=List[DesignerUserPointsResponse])
async def get_designer_points(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    filters: DesignerPointsRequest = Depends(),
    current_user: User = Depends(AuthenticateLeadDesigner()),
):
    return await db_repo.lead_designer.get_completed_tasks(
        user_id=filters.user_id,
        team_id=filters.team_id,
        start_date=filters.start_date,
        end_date=filters.end_date,
        task_status=DesignerTaskStatus.COMPLETED,
    )


@lead_designer_router.get("/view_designers_load", response_model=list[DesignerLoadTaskSchema])
async def view_designers_load(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    is_my_teams: bool | None = None,
    current_user: User = Depends(AuthenticateLeadDesigner()),
) -> list[DesignerLoadTaskSchema]:
    return await db_repo.lead_designer.view_designers_load(is_my_teams=is_my_teams, user_id=current_user.id)


@lead_designer_router.get("/designers_by_team", response_model=list[DesignerShortResponseSchema])
async def get_designers_by_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: list[int] = Query(..., description="ID Team"),
    current_user: User = Depends(AuthenticateLeadDesigner()),
):
    return await db_repo.lead_designer.get_designers_by_team(team_id=team_id)


@lead_designer_router.post("/create_operational_task", response_model=DesignerTaskResponseSchema)
async def create_operational_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_info: CreateOperationDesignerTaskSchema,
    current_user: User = Depends(AuthenticateLeadDesigner()),
):
    task = await db_repo.lead_designer.create_operational_task(task_info=task_info, user=current_user)

    await db_repo.designer_task_history.record_event(
        task_id=task.id,
        event=TaskEvent.TASK.value,
        event_info=TaskAction.CREATED.value,
        description=f"Task created by {current_user.username}",
        changed_by=current_user,
    )

    await db_repo.designer_task_history.record_event(
        task_id=task.id,
        event=TaskEvent.STATUS.value,
        event_info=task.task_status.value,
        description=f"Task status changed to {task.task_status.value} by {current_user.username}",
        changed_by=current_user,
    )
    return task
