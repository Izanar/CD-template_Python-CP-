import os
import re
import uuid
from typing import Annotated, List

from fastapi import APIRouter, Body, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependecies.auth import AuthenticateUser
from app.dependecies.stub import DatabaseRepositoryStub, S3BucketStub
from app.models import DesignerTask, User
from app.repository.database.base import DatabaseRepository
from app.repository.designers.task_history.utils import handle_event_info
from app.repository.media_buyers.tasks.utils import check_task_status
from app.repository.media_file.utils import check_archives_permission
from app.schemas.creative import CreativeResponseSchema
from app.schemas.enums.task_event import TaskAction, TaskEvent
from app.schemas.enums.task_status import DesignerTaskStatus, WebMasterTaskStatus
from app.schemas.media_buyers.tasks.designer_tasks import DesignerTaskResponseSchema
from app.schemas.media_buyers.tasks.web_master_tasks import WebMasterTaskResponseSchema
from app.schemas.media_file import MediaFileDeletePayload, MediaFileKeysPayload, MediaFileKeyUpdatePayload

media_files = APIRouter(
    prefix="/media_files",
    tags=["Media Files"],
)


@media_files.post("/web_master/{task_id}", response_model=WebMasterTaskResponseSchema)
async def add_web_master_media_file(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticateUser()),
    media_file: UploadFile | None = File(default=None),
    s3_bucket=Depends(S3BucketStub),
):
    existing_task = await db_repo.web_master_task.get_task(task_id=task_id, user=current_user)
    file_url = await s3_bucket.upload_image(media_file=media_file, task_info=existing_task)
    await db_repo.media_file.add_web_master_task_image(task_id=task_id, file_url=file_url)

    return await db_repo.web_master_task.get_task(task_id=task_id, user=current_user)


@media_files.patch("/web_master/{task_id}", response_model=WebMasterTaskResponseSchema)
async def update_web_master_media_file(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    file_id: int,
    media_file: UploadFile | None = File(default=None),
    current_user: User = Depends(AuthenticateUser()),
    s3_bucket=Depends(S3BucketStub),
):
    existing_task = await db_repo.web_master_task.get_task(task_id=task_id, user=current_user)
    await check_task_status(
        task=existing_task,
        allowed_statuses=[WebMasterTaskStatus.IN_PROGRESS, WebMasterTaskStatus.REQUESTED_CHANGES],
        detail="Task cannot be updated in its current status.",
    )
    old_media_file = await db_repo.media_file.get_file_by_id(file_id=file_id)
    new_file_url = await s3_bucket.update_image(
        old_file_url=old_media_file.file_url, new_media_file=media_file, task_info=existing_task
    )
    await db_repo.media_file.update_web_master_task_image(task_id=task_id, file_id=file_id, new_file_url=new_file_url)

    return await db_repo.web_master_task.get_task(task_id=task_id, user=current_user)


@media_files.delete("/web_master/{task_id}", response_model=WebMasterTaskResponseSchema)
async def remove_web_master_media_file(
    task_id: int,
    file_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateUser()),
    s3_bucket=Depends(S3BucketStub),
):
    old_media_file = await db_repo.media_file.get_file_by_id(file_id)
    await s3_bucket.delete_image(file_url=old_media_file.file_url)
    await db_repo.media_file.delete_web_master_task_image(task_id=task_id, file_id=file_id)

    return await db_repo.web_master_task.get_task(task_id=task_id, user=current_user)


@media_files.post("/designer/{task_id}", response_model=DesignerTaskResponseSchema)
async def add_designer_media_file(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    current_user: User = Depends(AuthenticateUser()),
    media_file: UploadFile | None = File(default=None),
    s3_bucket=Depends(S3BucketStub),
):
    existing_task = await db_repo.designer_task.get_task(task_id=task_id, user=current_user)

    await check_task_status(
        existing_task,
        allowed_statuses=[DesignerTaskStatus.IN_PROGRESS, DesignerTaskStatus.REQUESTED_CHANGES],
        detail=f"You can not change media file with current task status -- {existing_task.task_status.value}",
    )

    file_url = await s3_bucket.upload_image(media_file=media_file, task_info=existing_task)
    await db_repo.media_file.add_designer_task_image(task_id=task_id, file_url=file_url)

    return await db_repo.designer_task.get_task(task_id=task_id, user=current_user)


@media_files.post(
    "/designer/{task_id}/keys",
    response_model=DesignerTaskResponseSchema,
    summary="Attach S3 file keys to designer task",
)
async def add_designer_media_file_keys(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    payload: MediaFileKeysPayload = Body(...),
    current_user: User = Depends(AuthenticateUser()),
    s3_bucket=Depends(S3BucketStub),
):
    task = await db_repo.designer_task.get_task(task_id, user=current_user)
    await check_task_status(
        task,
        allowed_statuses=[DesignerTaskStatus.IN_PROGRESS, DesignerTaskStatus.REQUESTED_CHANGES],
        detail=f"You can not change media file with current task status -- {task.task_status.value}",
    )
    await check_archives_permission(task, payload.file_keys)

    await db_repo.media_file.add_designer_task_images(task_id, payload.file_keys, s3_bucket)

    await db_repo.designer_task_history.record_event(
        task_id=task_id,
        event=TaskEvent.MEDIA.value,
        event_info=handle_event_info(TaskEvent.MEDIA, action=TaskAction.ADDED),
        changed_by=current_user,
    )

    return await db_repo.designer_task.get_task(task_id, user=current_user)


@media_files.post(
    "/creative/{creative_id}/keys",
    response_model=CreativeResponseSchema,
    summary="Attach S3 file keys to creative",
)
async def add_creative_media_file_keys(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    creative_id: int,
    payload: MediaFileKeysPayload = Body(...),
    current_user: User = Depends(AuthenticateUser()),
    s3_bucket=Depends(S3BucketStub),
):
    creative = await db_repo.creative.get_creative_by_id(creative_id)
    task = await db_repo.designer_task.get_task(creative.task_id, user=current_user)

    await check_task_status(
        task,
        allowed_statuses=[DesignerTaskStatus.IN_PROGRESS, DesignerTaskStatus.REQUESTED_CHANGES],
        detail=f"You can not change media file with current task status -- {task.task_status.value}",
    )
    await check_archives_permission(task, payload.file_keys)

    await db_repo.creative.add_creative_files(creative_id, payload.file_keys, s3_bucket)

    await db_repo.designer_task_history.record_event(
        task_id=task.id,
        event=TaskEvent.MEDIA.value,
        event_info=handle_event_info(TaskEvent.MEDIA, action=TaskAction.ADDED),
        description=f"Creative files uploaded for creative {creative_id}",
        changed_by=current_user,
    )

    creative = await db_repo.creative.get_creative_by_id(creative_id)
    return CreativeResponseSchema.model_validate(creative)


@media_files.patch(
    "/creative/{creative_id}/keys",
    response_model=CreativeResponseSchema,
    summary="Update S3 key of creative media file",
)
async def update_creative_media_file_key(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    creative_id: int,
    payload: MediaFileKeyUpdatePayload = Body(...),
    current_user: User = Depends(AuthenticateUser()),
    s3_bucket=Depends(S3BucketStub),
):
    creative = await db_repo.creative.get_creative_by_id(creative_id)
    task = await db_repo.designer_task.get_task(creative.task_id, user=current_user)

    await check_task_status(
        task,
        allowed_statuses=[DesignerTaskStatus.IN_PROGRESS, DesignerTaskStatus.REQUESTED_CHANGES],
        detail=f"You can not change media file with current task status -- {task.task_status.value}",
    )
    await check_archives_permission(task, [payload.new_file_key])

    await db_repo.creative.update_creative_media_file(
        creative_id=creative_id,
        file_id=payload.file_id,
        new_file_key=payload.new_file_key,
        s3_bucket=s3_bucket,
    )

    await db_repo.designer_task_history.record_event(
        task_id=task.id,
        event=TaskEvent.MEDIA.value,
        event_info=handle_event_info(TaskEvent.MEDIA, action=TaskAction.UPDATED),
        description=f"Creative media file updated for creative {creative_id}",
        changed_by=current_user,
    )

    creative = await db_repo.creative.get_creative_by_id(creative_id)
    return CreativeResponseSchema.model_validate(creative)


@media_files.delete(
    "/creative/{creative_id}/keys",
    response_model=CreativeResponseSchema,
    summary="Remove media file from creative",
)
async def delete_creative_media_file_key(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    creative_id: int,
    payload: MediaFileDeletePayload = Body(...),
    current_user: User = Depends(AuthenticateUser()),
    s3_bucket=Depends(S3BucketStub),
):
    creative = await db_repo.creative.get_creative_by_id(creative_id)
    task = await db_repo.designer_task.get_task(creative.task_id, user=current_user)

    await check_task_status(
        task,
        allowed_statuses=[DesignerTaskStatus.IN_PROGRESS, DesignerTaskStatus.REQUESTED_CHANGES],
        detail=f"You can not change media file with current task status -- {task.task_status.value}",
    )

    for file_id in payload.file_ids:
        await db_repo.creative.delete_creative_media_file(
            creative_id=creative_id,
            file_id=file_id,
            s3_bucket=s3_bucket,
        )

    await db_repo.designer_task_history.record_event(
        task_id=task.id,
        event=TaskEvent.MEDIA.value,
        event_info=handle_event_info(TaskEvent.MEDIA, action=TaskAction.DELETED),
        description=f"Creative media files deleted for creative {creative_id}",
        changed_by=current_user,
    )

    creative = await db_repo.creative.get_creative_by_id(creative_id)
    return CreativeResponseSchema.model_validate(creative)


@media_files.patch(
    "/designer/{task_id}/keys",
    response_model=DesignerTaskResponseSchema,
    summary="Replace S3 key of one media file",
)
async def update_designer_media_file_key(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    payload: MediaFileKeyUpdatePayload = Body(...),
    current_user: User = Depends(AuthenticateUser()),
    s3_bucket=Depends(S3BucketStub),
):
    task = await db_repo.designer_task.get_task(task_id=task_id, user=current_user)
    await check_task_status(
        task,
        allowed_statuses=[DesignerTaskStatus.IN_PROGRESS, DesignerTaskStatus.REQUESTED_CHANGES],
        detail=f"You can not change media file with current task status -- {task.task_status.value}",
    )
    await check_archives_permission(task, [payload.new_file_key])

    await db_repo.media_file.update_designer_task_image_key(
        task_id=task_id,
        file_id=payload.file_id,
        new_file_key=payload.new_file_key,
        s3_bucket=s3_bucket,
    )

    await db_repo.designer_task_history.record_event(
        task_id=task_id,
        event=TaskEvent.MEDIA.value,
        event_info=handle_event_info(TaskEvent.MEDIA, action=TaskAction.UPDATED),
        changed_by=current_user,
    )

    return await db_repo.designer_task.get_task(task_id=task_id, user=current_user)


@media_files.delete(
    "/designer/{task_id}/keys",
    response_model=DesignerTaskResponseSchema,
    summary="Remove media files from designer task",
)
async def delete_designer_media_file_keys(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    payload: MediaFileDeletePayload = Body(...),
    current_user: User = Depends(AuthenticateUser()),
):
    task = await db_repo.designer_task.get_task(task_id, user=current_user)
    await check_task_status(
        task,
        allowed_statuses=[DesignerTaskStatus.IN_PROGRESS, DesignerTaskStatus.REQUESTED_CHANGES],
        detail=f"You can not change media file with current task status -- {task.task_status.value}",
    )
    await db_repo.media_file.delete_designer_task_images(task_id, payload.file_ids)

    await db_repo.designer_task_history.record_event(
        task_id=task_id,
        event=TaskEvent.MEDIA.value,
        event_info=handle_event_info(TaskEvent.MEDIA, action=TaskAction.DELETED),
        changed_by=current_user,
    )
    return await db_repo.designer_task.get_task(task_id, user=current_user)


@media_files.patch("/designer/{task_id}", response_model=DesignerTaskResponseSchema)
async def update_designer_media_file(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    task_id: int,
    file_id: int,
    media_file: UploadFile | None = File(default=None),
    current_user: User = Depends(AuthenticateUser()),
    s3_bucket=Depends(S3BucketStub),
):
    existing_task = await db_repo.designer_task.get_task(task_id=task_id, user=current_user)

    await check_task_status(
        existing_task,
        allowed_statuses=[DesignerTaskStatus.IN_PROGRESS, DesignerTaskStatus.REQUESTED_CHANGES],
        detail=f"You can not change media file with current task status -- {existing_task.task_status.value}",
    )
    old_media_file = await db_repo.media_file.get_file_by_id(file_id=file_id)
    new_file_url = await s3_bucket.update_image(
        old_file_url=old_media_file.file_url, new_media_file=media_file, task_info=existing_task
    )
    await db_repo.media_file.update_designer_task_image(task_id=task_id, file_id=file_id, new_file_url=new_file_url)

    return await db_repo.designer_task.get_task(task_id=task_id, user=current_user)


@media_files.delete("/designer/{task_id}", response_model=DesignerTaskResponseSchema)
async def remove_designer_media_file(
    task_id: int,
    file_id: int,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateUser()),
    s3_bucket=Depends(S3BucketStub),
):
    existing_task = await db_repo.designer_task.get_task(task_id=task_id, user=current_user)

    await check_task_status(
        existing_task,
        allowed_statuses=[DesignerTaskStatus.IN_PROGRESS, DesignerTaskStatus.REQUESTED_CHANGES],
        detail=f"You can not change media file with current task status -- {existing_task.task_status.value}",
    )

    old_media_file = await db_repo.media_file.get_file_by_id(file_id=file_id)
    await s3_bucket.delete_image(file_url=old_media_file.file_url)
    await db_repo.media_file.delete_designer_task_image(task_id=task_id, file_id=file_id)

    return await db_repo.designer_task.get_task(task_id=task_id, user=current_user)


@media_files.post("/admin/migrate_all_designer_uuids", status_code=status.HTTP_202_ACCEPTED, response_model=dict)
async def migrate_all_designer_uuids(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    s3_bucket=Depends(S3BucketStub),
    current_user: User = Depends(AuthenticateUser()),
):
    bucket_name: str = s3_bucket.bucket_name
    s3 = s3_bucket.s3
    from dotenv import load_dotenv

    load_dotenv()
    env = os.getenv("ENV", "dev")
    async with db_repo.media_file.session_maker() as db:  # type: AsyncSession
        tasks: List[DesignerTask] = (
            (
                await db.execute(
                    select(DesignerTask)
                    .options(selectinload(DesignerTask.media_files))
                    .where(DesignerTask.uuid.is_(None))
                )
            )
            .scalars()
            .all()
        )

        if not tasks:
            return {"detail": "Нет задач с NULL-uuid – мигрировать нечего"}

        migrated_tasks = []
        total_migrated_files = 0

        for task in tasks:
            new_uuid = uuid.uuid4()

            old_prefix = f"uploads/{task.id}/"
            new_prefix = f"uploads/{env}/{new_uuid}/"

            bucket = await s3.Bucket(bucket_name)
            migrated_files: List[dict] = []

            for mf in task.media_files:
                try:
                    key = mf.file_url.split(f"{bucket_name}.s3.amazonaws.com/")[1]
                except IndexError:
                    continue

                if key.startswith(new_prefix):
                    continue

                new_key = re.sub(rf"^{re.escape(old_prefix)}", new_prefix, key, count=1)

                await bucket.copy({"Bucket": bucket_name, "Key": key}, new_key)
                obj = await bucket.Object(key)
                await obj.delete()

                old_url = mf.file_url
                new_url = f"https://{bucket_name}.s3.amazonaws.com/{new_key}"
                mf.file_url = new_url
                migrated_files.append({"old": old_url, "new": new_url})

            task.uuid = new_uuid
            await db.commit()

            migrated_tasks.append({"task_id": task.id, "new_uuid": str(new_uuid), "files_updated": migrated_files})
            total_migrated_files += len(migrated_files)

    return {
        "migrated_tasks": migrated_tasks,
        "total_files_updated": total_migrated_files,
        "detail": "OK – все задачи с NULL-uuid мигрированы",
    }
