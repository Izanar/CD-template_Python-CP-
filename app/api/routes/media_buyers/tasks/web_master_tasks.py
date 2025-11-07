from datetime import date
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependecies.auth import (
    AuthenticateMainRoles,
    AuthenticateMediaBuyer,
    AuthenticateMediaBuyerOrLead,
    AuthenticateMediaBuyers,
    AuthenticateWebMasterTasksRoles,
)
from app.dependecies.stub import DatabaseRepositoryStub
from app.repository.database.base import DatabaseRepository
from app.repository.designers.task_history.utils import handle_event_info
from app.repository.media_buyers.tasks.utils import check_task_status
from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.enums.task_event import TaskEvent
from app.schemas.enums.task_status import WebMasterTaskStatus
from app.schemas.media_buyer import MediaBuyerTaskCreateSchema, WebMasterTaskCreateSchema
from app.schemas.media_buyers.tasks.web_master_tasks import (
    ApproveWebMasterTaskEditSchema,
    WebMasterTaskDeleteResponseSchema,
    WebMasterTaskEditRequestSchema,
    WebMasterTaskResponseSchema,
    WebMasterTaskResponseSchemaWithCreator,
)
from app.schemas.pagination import PaginationResponse
from app.schemas.user import User

buyer_web_master_tasks_router = APIRouter(
    prefix="/media_buyer/web_master",
    tags=["Media Buyer"],
)
logger = structlog.get_logger(__name__)


@buyer_web_master_tasks_router.post("/create", response_model=WebMasterTaskResponseSchema)
async def create_web_master_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task: WebMasterTaskCreateSchema,
    current_user: User = Depends(AuthenticateMediaBuyers()),
):
    created_task = await db_repo.web_master_task.create_task(
        task=task, user=current_user, task_status=WebMasterTaskStatus.WAITING_TO_ASSIGN
    )
    return created_task


@buyer_web_master_tasks_router.post("/create_draft", response_model=WebMasterTaskResponseSchema)
async def create_web_master_task_draft(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task: WebMasterTaskCreateSchema,
    current_user: User = Depends(AuthenticateMediaBuyer()),
):
    created_task = await db_repo.web_master_task.create_task(
        task=task, user=current_user, task_status=WebMasterTaskStatus.DRAFT
    )
    return created_task


@buyer_web_master_tasks_router.patch("/{task_id}/send", response_model=WebMasterTaskResponseSchema)
async def send_web_master_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticateMediaBuyer()),
):
    sent_task = await db_repo.web_master_task.send_task(task_id=task_id, user=current_user)
    return sent_task


@buyer_web_master_tasks_router.patch("/{task_id}/save-send", response_model=WebMasterTaskResponseSchema)
async def save_and_send_web_master_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    task: MediaBuyerTaskCreateSchema,
    current_user: User = Depends(AuthenticateMediaBuyer()),
):
    sent_task = await db_repo.web_master_task.save_and_send_task(task=task, task_id=task_id, user=current_user)
    return sent_task


@buyer_web_master_tasks_router.get("/tasks", response_model=PaginationResponse[WebMasterTaskResponseSchemaWithCreator])
async def get_web_master_tasks(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateWebMasterTasksRoles()),
    task_type: int = Query(None, description="Task type ID"),
    task_status: list[WebMasterTaskStatus] | None = Query(
        None, description="Filter by one or more task statuses EXAMPLE: (task_status=DRAFT&task_status=IN_PROGRESS)"
    ),
    limit: int = Query(10, ge=1, le=100, description="Limit of tasks per page"),
    offset: int = Query(0, ge=0, description="Offset of tasks"),
    order_by: Literal[
        "id",
        "title",
        "created_at",
        "deadline",
        "task_status",
        "is_high_priority",
        "difficulty_points",
        "created_by_username",
        "assigned_to_username",
        "assigned_to_rating",
        "vertical",
        "geo_code",
        "funnel_name",
        "celebrity_name",
        "site_name",
    ]
    | None = Query(
        None,
        description=(
            "Sort column: id|title|created_at|deadline|task_status|is_high_priority|"
            "difficulty_points|created_by_username|assigned_to_username|assigned_to_rating|"
            "vertical|geo_code|funnel_name|celebrity_name|site_name"
        ),
    ),
    order_direction: Literal["asc", "desc"] | None = Query("desc", description="Order direction"),
    created_from: date | None = Query(None, description="Created from this date (YYYY-MM-DD)"),
    created_to: date | None = Query(None, description="Created to this date (YYYY-MM-DD)"),
    is_media_buyers_teams: bool = Query(
        None, description="Get all tasks from media buyers teams ( Only for web_master leads )"
    ),
    is_need_to_assign: bool | None = Query(
        None, description="Tasks which need to assign ( Only for web_master leads )"
    ),
    is_high_priority: bool | None = Query(None, description="Tasks which have high priority"),
    created_by_id: int = Query(None, description="Filter by creator ID ( Only for web_master leads )"),
    buyer_team_id: int = Query(None, description="Filter by buyer team ID ( Only for web_master leads )"),
    assigned_to_id: int = Query(None, description="Filter by assigned to ID ( Only for web_master leads )"),
    title: str | None = Query(None, description="Filter by task title"),
    is_deleted: bool | None = Query(None, description="Show deleted tasks ( Only for admin )"),
    vertical: VerticalType | None = Query(
        None, description="Filter by vertical (e.g., crypto, gambling, nutra, google)"
    ),
    funnel_ids: list[int] | None = Query(None, description="Filter by one or more funnel IDs"),
    celebrity_ids: list[int] | None = Query(None, description="Filter by one or more celebrity IDs"),
    site_name_ids: list[int] | None = Query(None, description="Filter by one or more site‑name IDs"),
    geo_codes: list[int] | None = Query(None, description="Filter by one or more geo id's"),
):
    tasks, total = await db_repo.web_master_task.get_user_tasks(
        user=current_user,
        limit=limit,
        offset=offset,
        task_type=task_type,
        task_statuses=task_status,
        order_by=order_by,
        order_direction=order_direction,
        created_from=created_from,
        created_to=created_to,
        is_media_buyers_teams=is_media_buyers_teams,
        is_need_to_assign=is_need_to_assign,
        is_high_priority=is_high_priority,
        created_by_id=created_by_id,
        buyer_team_id=buyer_team_id,
        assigned_to_id=assigned_to_id,
        title=title,
        vertical=vertical,
        funnel_ids=funnel_ids,
        celebrity_ids=celebrity_ids,
        site_name_ids=site_name_ids,
        is_deleted=is_deleted,
        geo_codes=geo_codes,
    )

    tasks_schema = [WebMasterTaskResponseSchemaWithCreator.model_validate(task, from_attributes=True) for task in tasks]

    return PaginationResponse.create(items=tasks_schema, total=total, limit=limit, offset=offset)


@buyer_web_master_tasks_router.get("/{task_id}", response_model=WebMasterTaskResponseSchemaWithCreator)
async def get_web_master_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int | None = None,
    current_user: User = Depends(AuthenticateWebMasterTasksRoles()),
):
    return await db_repo.web_master_task.get_task(task_id=task_id, user=current_user)


@buyer_web_master_tasks_router.patch("/{task_id}/update", response_model=WebMasterTaskResponseSchema)
async def update_web_master_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task: WebMasterTaskCreateSchema,
    task_id: int,
    current_user: User = Depends(AuthenticateMainRoles()),
):
    updated_task = await db_repo.web_master_task.update_task(task=task, task_id=task_id, user=current_user)
    return updated_task


@buyer_web_master_tasks_router.post("/{task_id}/approve", response_model=WebMasterTaskResponseSchema)
async def approve_web_master_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticateMediaBuyer()),
):
    existing_task = await db_repo.web_master_task.get_task(task_id=task_id, user=current_user)

    await check_task_status(
        task=existing_task,
        required_status=WebMasterTaskStatus.UNDER_BUYER_REVIEW,
        detail=f"You can not change task with current task status -- {existing_task.task_status.value}",
    )

    if updated_task := await db_repo.web_master.update_task_status(
        task_id=task_id,
        task_status=WebMasterTaskStatus.COMPLETED,
        current_user=current_user,
    ):
        logger.info(f"User {current_user.username} updated task {task_id} status to {WebMasterTaskStatus.COMPLETED}")

        await db_repo.web_master_task_history.record_event(
            task_id=task_id,
            event=TaskEvent.STATUS_CHANGE.value,
            event_info=handle_event_info(event=TaskEvent.STATUS_CHANGE, new_status=WebMasterTaskStatus.COMPLETED.value),
            changed_by=current_user,
        )

        return updated_task

    return HTTPException(status_code=404, detail="Task not found")


@buyer_web_master_tasks_router.post(
    "/request_task_edit/{task_id}",
    response_model=WebMasterTaskResponseSchema,
    status_code=200,
)
async def request_web_master_task_edit(
    task_id: int,
    data: WebMasterTaskEditRequestSchema,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateMediaBuyerOrLead()),
):
    existing_task = await db_repo.web_master_task.get_task(task_id=task_id, user=current_user)

    await check_task_status(
        task=existing_task,
        required_status=WebMasterTaskStatus.UNDER_BUYER_REVIEW,
        detail=f"You can not change task with current task status -- {existing_task.task_status.value}",
    )

    requested_edit_task = await db_repo.web_master_task.request_edit_task(
        current_user=current_user, task_id=task_id, description=data.description
    )
    await db_repo.web_master_task_history.record_event(
        task_id=task_id,
        event=TaskEvent.STATUS_CHANGE.value,
        event_info=handle_event_info(event=TaskEvent.STATUS_CHANGE, new_status=WebMasterTaskStatus.IN_PROGRESS.value),
        changed_by=current_user,
    )
    return requested_edit_task


@buyer_web_master_tasks_router.post(
    "/approve_task_edit",
    response_model=WebMasterTaskResponseSchema,
    status_code=200,
)
async def approve_web_master_task_edit(
    data: ApproveWebMasterTaskEditSchema,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateMediaBuyerOrLead()),
):
    existing_task = await db_repo.web_master_task.get_task(task_id=data.task_id, user=current_user)

    await check_task_status(
        task=existing_task,
        required_status=WebMasterTaskStatus.UNDER_BUYER_REVIEW,
        detail=f"You can not change task with current task status -- {existing_task.task_status.value}",
    )

    approved_requested_edit_task = await db_repo.web_master_task.approve_edit_task(
        current_user=current_user, edit_id=data.edit_id, task_id=data.task_id
    )
    await db_repo.web_master_task_history.record_event(
        task_id=data.task_id,
        event=TaskEvent.EDIT_APPROVED.value,
        event_info=handle_event_info(event=TaskEvent.EDIT_APPROVED, edit_id=str(data.edit_id)),
        changed_by=current_user,
    )
    return approved_requested_edit_task


@buyer_web_master_tasks_router.delete("/{task_id}/remove", response_model=WebMasterTaskDeleteResponseSchema)
async def remove_web_master_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticateMediaBuyerOrLead()),
):
    task = await db_repo.web_master_task.delete_task(task_id=task_id, user=current_user)

    return WebMasterTaskDeleteResponseSchema(task_id=task.id)
