from typing import Annotated, List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependecies.auth import AuthenticateLeadWebMaster
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.repository.designers.task_history.utils import handle_event_info
from app.schemas.enums.task_event import TaskEvent
from app.schemas.enums.task_status import WebMasterTaskStatus
from app.schemas.lead_web_master import (
    WebMasterLoadTaskSchema,
    WebMasterShortResponseSchema,
)
from app.schemas.media_buyers.tasks.web_master_tasks import (
    UpdateWebMasterTaskSchema,
    WebMasterPointsRequest,
    WebMasterTaskResponseSchema,
    WebMasterUserPointsResponse,
)

lead_web_master_router = APIRouter(
    prefix="/lead_web_master",
    tags=["Lead Web Master"],
)


logger = structlog.get_logger(__name__)


@lead_web_master_router.post("/task/{task_id}/approve", response_model=WebMasterTaskResponseSchema)
async def approve_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticateLeadWebMaster()),
):
    if updated_task := await db_repo.web_master.update_task_status(
        task_id=task_id,
        task_status=WebMasterTaskStatus.UNDER_BUYER_REVIEW,
        current_user=current_user,
    ):
        logger.info(
            f"User {current_user.username} updated task {task_id} status to {WebMasterTaskStatus.UNDER_BUYER_REVIEW}"
        )

        await db_repo.web_master_task_history.record_event(
            task_id=task_id,
            event=TaskEvent.STATUS_CHANGE.value,
            event_info=handle_event_info(
                event=TaskEvent.STATUS_CHANGE, new_status=WebMasterTaskStatus.UNDER_BUYER_REVIEW.value
            ),
            changed_by=current_user,
        )

        return updated_task

    return HTTPException(status_code=404, detail="Task not found")


@lead_web_master_router.post("/task/{task_id}/request_changes", response_model=WebMasterTaskResponseSchema)
async def request_changes_on_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticateLeadWebMaster()),
):
    if updated_task := await db_repo.web_master.update_task_status(
        task_id=task_id,
        task_status=WebMasterTaskStatus.REQUESTED_CHANGES,
        current_user=current_user,
    ):
        logger.info(
            f"User {current_user.username} updated task {task_id} status to {WebMasterTaskStatus.REQUESTED_CHANGES}"
        )

        await db_repo.web_master_task_history.record_event(
            task_id=task_id,
            event=TaskEvent.STATUS_CHANGE.value,
            event_info=handle_event_info(
                event=TaskEvent.STATUS_CHANGE, new_status=WebMasterTaskStatus.REQUESTED_CHANGES.value
            ),
            changed_by=current_user,
        )

        return updated_task

    return HTTPException(status_code=404, detail="Task not found")


@lead_web_master_router.patch("/task/update", response_model=WebMasterTaskResponseSchema)
async def update_web_master_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_info: UpdateWebMasterTaskSchema,
    current_user: User = Depends(AuthenticateLeadWebMaster()),
):
    await db_repo.web_master_task_history.record_event(
        task_id=task_info.task_id,
        event=TaskEvent.UPDATE.value,
        event_info=handle_event_info(event=TaskEvent.UPDATE),
        changed_by=current_user,
    )
    return await db_repo.lead_web_master.update_web_master_task(task_info=task_info, user=current_user)


@lead_web_master_router.get("/web_master_points", response_model=List[WebMasterUserPointsResponse])
async def get_web_master_points(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    filters: WebMasterPointsRequest = Depends(),
    current_user: User = Depends(AuthenticateLeadWebMaster()),
):
    return await db_repo.lead_web_master.get_completed_tasks(
        user_id=filters.user_id,
        team_id=filters.team_id,
        start_date=filters.start_date,
        end_date=filters.end_date,
        task_status=WebMasterTaskStatus.COMPLETED,
    )


@lead_web_master_router.get("/view_web_master_load", response_model=list[WebMasterLoadTaskSchema])
async def view_web_master_load(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    is_my_teams: bool | None = None,
    current_user: User = Depends(AuthenticateLeadWebMaster()),
) -> list[WebMasterLoadTaskSchema]:
    return await db_repo.lead_web_master.view_web_master_load(is_my_teams=is_my_teams, user_id=current_user.id)


@lead_web_master_router.get("/web_masters_by_team", response_model=list[WebMasterShortResponseSchema])
async def get_web_masters_by_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int = Query(..., description="Team ID"),
    current_user: User = Depends(AuthenticateLeadWebMaster()),
):
    return await db_repo.lead_web_master.get_web_masters_by_team(team_id=team_id)
