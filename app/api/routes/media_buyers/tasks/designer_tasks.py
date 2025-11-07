from datetime import date
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query

from app.dependecies.auth import (
    AuthenticatedDesignerTasksRoles,
    AuthenticateMediaBuyerLeadOrLeadDesigner,
    AuthenticateMediaBuyerOrLead,
    AuthenticateMediaBuyers,
)
from app.dependecies.description_media_service import get_description_media_service
from app.dependecies.notifications import get_notification_service
from app.dependecies.stub import DatabaseRepositoryStub, S3BucketStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.repository.media_buyers.tasks.utils import check_task_status, get_task_creation_description
from app.repository.media_file.utils import ensure_files_exist
from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.enums.task_event import TaskAction, TaskEvent
from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.task_type import DesignerTaskTypeEnum
from app.schemas.media_buyer import (
    MediaBuyerTaskCreateSchema,
    MediaBuyerTaskUpdateSchema,
    MediaBuyerTaskWithCreativesCreateSchema,
)
from app.schemas.media_buyers.tasks.designer_tasks import (
    ApproveDesignerTaskEditSchema,
    ApproveTaskSchema,
    DesignerTaskDeleteResponseSchema,
    DesignerTaskEditRequestSchema,
    DesignerTaskResponseSchema,
    DesignerTaskResponseSchemaWithCreator,
)
from app.schemas.pagination import PaginationResponse
from app.services.notifications import NotificationService
from app.services.tasks.description_media import DescriptionMediaOnCreateService

buyer_designer_tasks_router = APIRouter(
    prefix="/media_buyer/designer",
    tags=["Media Buyer"],
)

logger = structlog.get_logger(__name__)


@buyer_designer_tasks_router.post("/create", response_model=DesignerTaskResponseSchema)
async def create_designer_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task: MediaBuyerTaskWithCreativesCreateSchema,
    description_media_service: Annotated[DescriptionMediaOnCreateService, Depends(get_description_media_service)],
    current_user: User = Depends(AuthenticateMediaBuyers()),
    s3_bucket=Depends(S3BucketStub),
):
    if task.description_files:
        await ensure_files_exist(task.description_files, s3_bucket)

    created_task = await db_repo.designer_task.create_task(
        task=task, user=current_user, task_status=DesignerTaskStatus.WAITING_TO_ASSIGN
    )

    # Создаем креативы, если они есть
    if task.creatives:
        await db_repo.creative.create_creatives_batch(task.creatives, created_task.id)

    if task.description_files:
        final_keys = await description_media_service.attach(
            task_id=created_task.id,
            task_uuid=created_task.uuid,
            temp_keys=task.description_files,
        )
        if final_keys:
            await db_repo.designer_task_history.record_event(
                task_id=created_task.id,
                event=TaskEvent.MEDIA.value,
                event_info=TaskAction.ADDED.value,
                description="Description media attached on task creation",
                changed_by=current_user,
            )

    task_description = get_task_creation_description(task.creatives, current_user.username)

    await db_repo.designer_task_history.record_event(
        task_id=created_task.id,
        event=TaskEvent.TASK.value,
        event_info=TaskAction.CREATED.value,
        description=task_description,
        changed_by=current_user,
    )

    await db_repo.designer_task_history.record_event(
        task_id=created_task.id,
        event=TaskEvent.STATUS.value,
        event_info=created_task.task_status.value,
        description=f"Task status changed to {created_task.task_status.value} by {current_user.username}",
        changed_by=current_user,
    )
    return await db_repo.designer_task.get_task(created_task.id, user=current_user)


@buyer_designer_tasks_router.post("/create_draft", response_model=DesignerTaskResponseSchema)
async def create_designer_task_draft(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task: MediaBuyerTaskCreateSchema,
    description_media_service: Annotated[DescriptionMediaOnCreateService, Depends(get_description_media_service)],
    current_user: User = Depends(AuthenticateMediaBuyers()),
    s3_bucket=Depends(S3BucketStub),
):
    if task.description_files:
        await ensure_files_exist(task.description_files, s3_bucket)

    created_task = await db_repo.designer_task.create_draft_task(
        task=task, user=current_user, task_status=DesignerTaskStatus.DRAFT
    )

    if task.description_files:
        final_keys = await description_media_service.attach(
            task_id=created_task.id,
            task_uuid=created_task.uuid,
            temp_keys=task.description_files,
        )
        if final_keys:
            await db_repo.designer_task_history.record_event(
                task_id=created_task.id,
                event=TaskEvent.MEDIA.value,
                event_info=TaskAction.ADDED.value,
                description="Description media attached on task creation",
                changed_by=current_user,
            )

    await db_repo.designer_task_history.record_event(
        task_id=created_task.id,
        event=TaskEvent.TASK.value,
        event_info=TaskAction.CREATED.value,
        description=f"Task created by {current_user.username}",
        changed_by=current_user,
    )

    await db_repo.designer_task_history.record_event(
        task_id=created_task.id,
        event=TaskEvent.STATUS.value,
        event_info=created_task.task_status.value,
        description=f"Task status changed to {created_task.task_status.value} by {current_user.username}",
        changed_by=current_user,
    )
    return await db_repo.designer_task.get_task(created_task.id, user=current_user)


@buyer_designer_tasks_router.patch("/{task_id}/send", response_model=DesignerTaskResponseSchema)
async def send_designer_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticateMediaBuyers()),
):
    sent_task = await db_repo.designer_task.send_task(task_id=task_id, user=current_user)
    await db_repo.designer_task_history.record_event(
        task_id=task_id,
        event=TaskEvent.STATUS.value,
        event_info=sent_task.task_status.value,
        description=f"Task status changed to {sent_task.task_status.value} by {current_user.username}",
        changed_by=current_user,
    )

    return sent_task


@buyer_designer_tasks_router.patch("/{task_id}/save-send", response_model=DesignerTaskResponseSchema)
async def save_and_send_designer_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    task: MediaBuyerTaskCreateSchema,
    current_user: User = Depends(AuthenticateMediaBuyers()),
):
    sent_task = await db_repo.designer_task.save_and_send_task(task=task, task_id=task_id, user=current_user)
    await db_repo.designer_task_history.record_event(
        task_id=task_id,
        event=TaskEvent.STATUS.value,
        event_info=sent_task.task_status.value,
        description=f"Task status changed to {sent_task.task_status.value} by {current_user.username}",
        changed_by=current_user,
    )
    return sent_task


@buyer_designer_tasks_router.get(
    "/tasks",
    response_model=PaginationResponse[DesignerTaskResponseSchemaWithCreator],
)
async def get_designer_tasks(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticatedDesignerTasksRoles()),
    task_type: DesignerTaskTypeEnum = Query(None, description="Task type enum"),
    task_status: list[DesignerTaskStatus] | None = Query(
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
    ]
    | None = Query(
        None,
        description="Sort column: id|title|created_at|deadline|task_status|is_high_priority|"
        "difficulty_points|created_by_name|assigned_to_name|assigned_to_rating",
    ),
    order_direction: Literal["asc", "desc"] | None = Query("desc", description="Order direction"),
    created_from: date | None = Query(None, description="Created from this date (YYYY-MM-DD)"),
    created_to: date | None = Query(None, description="Created to this date (YYYY-MM-DD)"),
    is_media_buyers_teams: bool = Query(
        None, description="Get all tasks from media buyers teams ( Only for designer leads )"
    ),
    is_need_to_assign: bool | None = Query(None, description="Tasks which need to assign ( Only for designer leads )"),
    is_high_priority: bool | None = Query(None, description="Tasks which have high priority"),
    created_by_id: list[int] | None = Query(None, description="Filter by creator ID ( Only for designer leads )"),
    buyer_team_ids: list[int] | None = Query(None, description="Filter by one or more MEDIA-BUYER team IDs"),
    assigned_to_id: list[int] = Query(None, description="Filter by assigned to ID ( Only for designer leads )"),
    title: str | None = Query(None, description="Filter by task title"),
    is_operational: bool | None = Query(None, description="Filter by tasks which are operational"),
    is_deleted: bool | None = Query(None, description="Show deleted tasks ( Only for admin )"),
    difficulty_ids: list[int] | None = Query(
        None,
        description="Filter by one or more difficulty level IDs (designer-only). "
        "Example: ?difficulty_ids=1&difficulty_ids=3",
    ),
    designer_team_ids: list[int] | None = Query(
        None,
        description="Filter by one or more DESIGNER team IDs",
    ),
    vertical: VerticalType | None = Query(
        None, description="Filter by vertical (e.g., crypto, gambling, nutra, google)"
    ),
    geo_codes: list[int] | None = Query(None, description="Filter by one or more geo id's"),
    ad_name: str | None = Query(None, description="Filter by ad name in creatives"),
):
    tasks, total = await db_repo.designer_task.get_user_tasks(
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
        buyer_team_ids=buyer_team_ids,
        assigned_to_id=assigned_to_id,
        title=title,
        is_operational=is_operational,
        is_deleted=is_deleted,
        difficulty_ids=difficulty_ids,
        designer_team_ids=designer_team_ids,
        vertical=vertical,
        geo_codes=geo_codes,
        ad_name=ad_name,
    )
    tasks_schema = [DesignerTaskResponseSchemaWithCreator.model_validate(task, from_attributes=True) for task in tasks]

    return PaginationResponse.create(items=tasks_schema, total=total, limit=limit, offset=offset)


@buyer_designer_tasks_router.get("/{task_id}", response_model=DesignerTaskResponseSchemaWithCreator)
async def get_designer_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int | None = None,
    current_user: User = Depends(AuthenticatedDesignerTasksRoles()),
):
    return await db_repo.designer_task.get_task(task_id=task_id, user=current_user)


@buyer_designer_tasks_router.patch("/{task_id}/update", response_model=DesignerTaskResponseSchema)
async def update_designer_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task: MediaBuyerTaskUpdateSchema,
    task_id: int,
    current_user: User = Depends(AuthenticateMediaBuyers()),
):
    updated_task = await db_repo.designer_task.update_task(task=task, task_id=task_id, user=current_user)

    await db_repo.designer_task_history.record_event(
        task_id=task_id,
        event=TaskEvent.TASK.value,
        event_info=TaskAction.UPDATED.value,
        description=f"Task updated by {current_user.username}",
        changed_by=current_user,
    )

    return updated_task


@buyer_designer_tasks_router.post("/{task_id}/approve", response_model=DesignerTaskResponseSchema)
async def approve_designer_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    data: ApproveTaskSchema,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(AuthenticateMediaBuyerOrLead()),
    notification_service: NotificationService = Depends(get_notification_service),
    s3_bucket=Depends(S3BucketStub),
):
    existing_task = await db_repo.designer_task.get_task(task_id=task_id, user=current_user)
    await check_task_status(
        task=existing_task,
        required_status=DesignerTaskStatus.UNDER_BUYER_REVIEW,
        detail=f"You can not change task with current task status -- {existing_task.task_status.value}",
    )

    if updated_task := await db_repo.designer.update_task_status(
        task_id=task_id,
        task_status=DesignerTaskStatus.COMPLETED,
        current_user=current_user,
        rating=data.rating,
        comment=data.comment,
    ):
        description = (
            f"Task approved by {current_user.username}"
            + (f" with rating {data.rating}" if data.rating else "")
            + (f": {data.comment}" if data.comment else "")
        )

        logger.info(f"User {current_user.username} updated task {task_id} status to {DesignerTaskStatus.COMPLETED}")

        await db_repo.designer_task_history.record_event(
            task_id=task_id,
            event=TaskEvent.STATUS.value,
            event_info=updated_task.task_status.value,
            description=description,
            changed_by=current_user,
        )
        background_tasks.add_task(notification_service.send_notification, updated_task)

        return updated_task

    return HTTPException(status_code=404, detail="Task not found")


@buyer_designer_tasks_router.post(
    "/request_task_edit/{task_id}",
    response_model=DesignerTaskResponseSchema,
    status_code=200,
)
async def request_designer_task_edit(
    task_id: int,
    data: DesignerTaskEditRequestSchema,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateMediaBuyerOrLead()),
):
    existing_task = await db_repo.designer_task.get_task(task_id=task_id, user=current_user)
    await check_task_status(
        task=existing_task,
        required_status=DesignerTaskStatus.UNDER_BUYER_REVIEW,
        detail=f"You can not change task with current task status -- {existing_task.task_status.value}",
    )
    """Request edit for the task."""
    requested_edit_task = await db_repo.designer_task.request_edit_task(
        current_user=current_user, task_id=task_id, description=data.description
    )
    await db_repo.designer_task_history.record_event(
        task_id=task_id,
        event=TaskEvent.EDIT.value,
        event_info=TaskAction.REQUESTED.value,
        description=f"Edit requested by {current_user.username}",
        changed_by=current_user,
    )
    await db_repo.designer_task_history.record_event(
        task_id=task_id,
        event=TaskEvent.STATUS.value,
        event_info=requested_edit_task.task_status.value,
        description=f"Task status changed to {requested_edit_task.task_status.value} by {current_user.username}",
        changed_by=current_user,
    )
    return requested_edit_task


@buyer_designer_tasks_router.post(
    "/approve_task_edit",
    response_model=DesignerTaskResponseSchema,
    status_code=200,
)
async def approve_designer_task_edit(
    data: ApproveDesignerTaskEditSchema,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateMediaBuyerOrLead()),
):
    existing_task = await db_repo.designer_task.get_task(task_id=data.task_id, user=current_user)
    await check_task_status(
        task=existing_task,
        required_status=DesignerTaskStatus.UNDER_BUYER_REVIEW,
        detail=f"You can not change task with current task status -- {existing_task.task_status.value}",
    )

    approved_requested_edit_task = await db_repo.designer_task.approve_edit_task(
        current_user=current_user, edit_id=data.edit_id, task_id=data.task_id
    )
    await db_repo.designer_task_history.record_event(
        task_id=data.task_id,
        event=TaskEvent.EDIT.value,
        event_info=TaskAction.APPROVED.value,
        description=f"Edit approved by {current_user.username}",
        changed_by=current_user,
    )
    return approved_requested_edit_task


@buyer_designer_tasks_router.delete("/{task_id}/remove", response_model=DesignerTaskDeleteResponseSchema)
async def remove_designer_task(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticateMediaBuyerLeadOrLeadDesigner()),
):
    task = await db_repo.designer_task.delete_task(task_id=task_id, user=current_user)
    await db_repo.designer_task_history.record_event(
        task_id=task_id,
        event=TaskEvent.TASK.value,
        event_info=TaskAction.DELETED.value,
        description=f"Task deleted by {current_user.username}",
        changed_by=current_user,
    )
    return DesignerTaskDeleteResponseSchema(task_id=task.id)


@buyer_designer_tasks_router.post(
    "/{task_id}/notes",
    response_model=DesignerTaskResponseSchemaWithCreator,
)
async def add_task_note(
    task_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticatedDesignerTasksRoles()),
    note: str = Body(..., embed=True),
):
    return await db_repo.designer_task.add_task_note(
        task_id=task_id,
        author=current_user,
        content=note,
    )
