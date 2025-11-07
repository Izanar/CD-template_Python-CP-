from fastapi import HTTPException, status

from app.models import User
from app.repository.media_buyers.tasks.utils import check_task_status
from app.schemas.enums.task_status import DesignerTaskStatus
from app.schemas.enums.user import UserRole


async def validate_creative_update_permissions(task, current_user: User, update_data=None) -> None:
    if current_user.role == UserRole.designer:
        if task.assigned_to_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not assigned to this task")
        await check_task_status(
            task,
            allowed_statuses=[DesignerTaskStatus.IN_PROGRESS],
            detail=f"You can not update creative with current task status -- {task.task_status.value}. "
            f"Only IN_PROGRESS tasks allow creative editing by designer.",
        )

    elif current_user.role in (UserRole.lead_designer, UserRole.admin):
        pass
    elif current_user.role in (UserRole.media_buyer, UserRole.lead_media_buyer):
        await check_task_status(
            task,
            allowed_statuses=[DesignerTaskStatus.COMPLETED],
            detail=f"You can not update creative with current task status -- {task.task_status.value}. "
            f"Only COMPLETED tasks allow creative editing.",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to update creatives"
        )
