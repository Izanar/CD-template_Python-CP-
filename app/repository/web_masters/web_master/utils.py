import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.models import MediaBuyer, User, WebMaster, WebMasterTask
from app.schemas.enums.user import UserRole

logger = structlog.get_logger(__name__)


async def get_task(db, task_id: int, user: User) -> WebMasterTask:
    stmt = (
        select(WebMasterTask)
        .where(WebMasterTask.id == task_id)
        .options(
            joinedload(WebMasterTask.funnel_ref),
            joinedload(WebMasterTask.site_name_ref),
            joinedload(WebMasterTask.celebrity_ref),
            joinedload(WebMasterTask.geo_ref),
            joinedload(WebMasterTask.buyer_team),
            selectinload(WebMasterTask.task_type),
            selectinload(WebMasterTask.media_files),
            selectinload(WebMasterTask.difficulties),
            selectinload(WebMasterTask.edits),
            selectinload(WebMasterTask.assigned_to).selectinload(WebMaster.user),
            selectinload(WebMasterTask.assigned_to).selectinload(WebMaster.teams),
            selectinload(WebMasterTask.created_by).selectinload(MediaBuyer.user),
        )
    )

    if task := await db.scalar(stmt):
        return task
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")


async def build_task_filters(user: User, task_id: int):
    filters = [WebMasterTask.id == task_id]

    if user.role == UserRole.web_master:
        filters.append(WebMasterTask.assigned_to_id == user.id)
    if user.role == UserRole.media_buyer:
        filters.append(WebMasterTask.created_by_id == user.id)

    return filters
