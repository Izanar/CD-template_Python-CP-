from typing import Annotated, List

import structlog
from fastapi import APIRouter, Depends

from app.dependecies.auth import AuthenticateLeadDesigner, AuthenticateLeadWebMaster
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.task_history import DesignerTaskHistoryResponseSchema, WebMasterTaskHistoryResponseSchema

logger = structlog.get_logger()

task_history_router = APIRouter(
    prefix="/task_history",
    tags=["Task History"],
)


@task_history_router.get(
    "/designer/{task_id}",
    response_model=List[DesignerTaskHistoryResponseSchema],
)
async def get_designer_task_history(
    task_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateLeadDesigner()),
):
    return await db_repo.designer_task_history.get_task_history(task_id)


@task_history_router.get("/web_master/{task_id}", response_model=list[WebMasterTaskHistoryResponseSchema])
async def get_web_master_task_history(
    task_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateLeadWebMaster()),
):
    """Get task history by task ID."""

    task_history = await db_repo.web_master_task_history.get_task_history(
        task_id=task_id,
    )

    return [
        WebMasterTaskHistoryResponseSchema(
            id=item["id"],
            task_id=item["task_id"],
            buyer=item["buyer_username"],
            lead=item["lead_username"],
            assigned_web_master=item["assigned_web_master_username"],
            event=item["event"],
            event_info=item["event_info"],
        )
        for item in task_history
    ]
