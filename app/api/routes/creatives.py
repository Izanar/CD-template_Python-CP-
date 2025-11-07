from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependecies.auth import AuthenticateUser
from app.dependecies.stub import DatabaseRepositoryStub, S3BucketStub
from app.models import User
from app.repository.creative.utils import validate_creative_update_permissions
from app.repository.database.base import DatabaseRepository
from app.repository.designers.task_history.utils import handle_event_info
from app.schemas.creative import CreativeCreateSchema, CreativeResponseSchema, CreativeUpdateSchema
from app.schemas.enums.task_event import TaskAction, TaskEvent

creatives_router = APIRouter(
    prefix="/creatives",
    tags=["Creatives"],
)


@creatives_router.post(
    "/create",
    response_model=list[CreativeResponseSchema],
    summary="Create creatives",
)
async def create_creatives(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    creatives_data: list[CreativeCreateSchema],
    current_user: User = Depends(AuthenticateUser()),
):
    if not creatives_data:
        return []

    task_id = creatives_data[0].task_id
    await db_repo.designer_task.get_task(task_id, user=current_user)

    created_creatives = await db_repo.creative.create_creatives_batch(creatives_data, task_id)

    await db_repo.designer_task_history.record_event(
        task_id=task_id,
        event=TaskEvent.MEDIA.value,
        event_info=handle_event_info(TaskEvent.MEDIA, action=TaskAction.CREATED),
        description=f"Created {len(created_creatives)} creatives for task {task_id} by {current_user.username}",
        changed_by=current_user,
    )

    return [CreativeResponseSchema.model_validate(creative) for creative in created_creatives]


@creatives_router.patch(
    "/{creative_id}",
    response_model=CreativeResponseSchema,
    summary="Update creative fields",
)
async def update_creative_fields(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    creative_id: int,
    update_data: CreativeUpdateSchema,
    current_user: User = Depends(AuthenticateUser()),
    s3_bucket=Depends(S3BucketStub),
):
    creative = await db_repo.creative.get_creative_by_id(creative_id)
    task = await db_repo.designer_task.get_task(creative.task_id, user=current_user)

    await validate_creative_update_permissions(task, current_user, update_data)

    updated_creative = await db_repo.creative.update_creative_fields(creative_id, update_data, s3_bucket)

    await db_repo.designer_task_history.record_event(
        task_id=task.id,
        event=TaskEvent.MEDIA.value,
        event_info=handle_event_info(TaskEvent.MEDIA, action=TaskAction.UPDATED),
        description=f"Creative {creative_id} fields updated by {current_user.username}",
        changed_by=current_user,
    )

    return CreativeResponseSchema.model_validate(updated_creative)
