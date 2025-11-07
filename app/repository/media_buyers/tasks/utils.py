from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DesignerTask,
    DesignerTaskStatus,
    User,
    WebMasterTask,
    WebMasterTaskStatus,
)
from app.schemas.enums.user import UserRole


async def check_task_status(
    task: DesignerTask | WebMasterTask,
    required_status: DesignerTaskStatus | WebMasterTaskStatus | None = None,
    forbidden_status: DesignerTaskStatus | WebMasterTaskStatus | None = None,
    allowed_statuses: list[DesignerTaskStatus | WebMasterTaskStatus] | None = None,
    status_code: int = 409,
    detail: str | None = None,
) -> None:
    if required_status is not None and task.task_status != required_status:
        default_detail = f"Task with ID {task.id} must be in {required_status.value} status."
        raise HTTPException(status_code=status_code, detail=detail or default_detail)

    if forbidden_status is not None and task.task_status == forbidden_status:
        default_detail = f"Task with ID {task.id} cannot be in {forbidden_status.value} status."
        raise HTTPException(status_code=status_code, detail=detail or default_detail)

    if allowed_statuses is not None and task.task_status not in allowed_statuses:
        status_list = ", ".join(s.value for s in allowed_statuses)
        default_detail = f"Task with ID {task.id} must be in one of the following statuses: {status_list}."
        raise HTTPException(status_code=status_code, detail=detail or default_detail)


async def ensure_task_was_updated(updated_task_id: int, detail: str):
    if not updated_task_id:
        raise HTTPException(status_code=400, detail=detail)


async def ensure_can_edit_priority(
    user: User,
    task: DesignerTask,
    update_data: dict,
    db: AsyncSession,
) -> None:
    if "is_high_priority" in update_data and user.role == UserRole.lead_media_buyer and task.created_by_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lead buyer cannot change priority for tasks created by other buyers.",
        )

    if update_data.get("is_high_priority") and not task.is_high_priority:
        high_priority_count = await db.scalar(
            select(func.count())
            .select_from(DesignerTask)
            .where(
                DesignerTask.created_by_id == task.created_by_id,
                DesignerTask.is_high_priority.is_(True),
                DesignerTask.is_deleted.is_(False),
                DesignerTask.id != task.id,
            )
        )
        if high_priority_count >= 5:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User already has {5} high-priority tasks.",
            )


def get_task_creation_description(task_creatives: list, username: str) -> str:
    creatives_count = len(task_creatives) if task_creatives else 0
    if creatives_count > 0:
        return f"Task with {creatives_count} creatives created by {username}"
    return f"Task created by {username}"
