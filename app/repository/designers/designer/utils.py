from typing import Any, List, Union

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import (
    Creative,
    Designer,
    DesignersTeamMembers,
    DesignerTask,
    DesignerTaskCelebrity,
    MediaBuyer,
    TaskEvaluation,
    User,
    WebMasterTask,
)
from app.repository.media_buyers.tasks.designer_tasks.utils import restrict_media_files
from app.schemas.enums.user import UserRole

logger = structlog.get_logger(__name__)


async def get_task(db, task_id: int, user: User) -> DesignerTask:
    stmt = (
        select(DesignerTask)
        .where(DesignerTask.id == task_id, DesignerTask.is_deleted.is_(False))
        .options(
            selectinload(DesignerTask.media_files),
            selectinload(DesignerTask.creatives).selectinload(Creative.media_files),
            selectinload(DesignerTask.difficulties),
            selectinload(DesignerTask.edits),
            selectinload(DesignerTask.evaluations),
            selectinload(DesignerTask.assigned_to).selectinload(Designer.user),
            selectinload(DesignerTask.assigned_to).selectinload(Designer.teams),
            selectinload(DesignerTask.created_by).selectinload(User.media_buyer),
            selectinload(DesignerTask.created_by).selectinload(User.media_buyer).selectinload(MediaBuyer.teams),
            selectinload(DesignerTask.celebrity_relations).selectinload(DesignerTaskCelebrity.celebrity),
            joinedload(DesignerTask.buyer_team),
        )
    )

    if task := await db.scalar(stmt):
        restrict_media_files(task=task, user=user)
        return task
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")


async def build_task_filters(current_user: User, task_id: int):
    filters = [DesignerTask.id == task_id]

    if current_user.role == UserRole.designer:
        filters.append(DesignerTask.assigned_to_id == current_user.id)
    if current_user.role == UserRole.media_buyer:
        filters.append(DesignerTask.created_by_id == current_user.id)

    return filters


async def filter_by_team_id(
    stmt,
    team_id: Union[int, List[int], None],
):
    if team_id is not None:
        if isinstance(team_id, int):
            stmt = stmt.join(
                DesignersTeamMembers,
                DesignersTeamMembers.designer_id == Designer.id,
            ).where(DesignersTeamMembers.team_id == team_id)
        elif isinstance(team_id, list):
            stmt = stmt.join(
                DesignersTeamMembers,
                DesignersTeamMembers.designer_id == Designer.id,
            ).where(DesignersTeamMembers.team_id.in_(team_id))
    return stmt


async def handle_task_evaluation(
    db: AsyncSession,
    task: Any,
    current_user: User,
    rating: int | None,
    comment: str | None,
):
    if not task.evaluation_required:
        return

    if task.is_operational:
        return

    role = current_user.role
    role_allowed = role in {UserRole.lead_media_buyer, UserRole.media_buyer}
    if role == UserRole.admin:
        pass
    elif not (current_user.id == task.created_by_id and role_allowed):
        raise HTTPException(status_code=403, detail="User not authorized to evaluate this task")

    if rating is None or comment is None:
        raise HTTPException(status_code=400, detail="Rating and comment are required for this task type")

    evaluation_kwargs = {
        "evaluator_id": current_user.id,
        "rating": rating,
        "comment": comment,
    }

    if isinstance(task, DesignerTask):
        evaluation_kwargs["designer_task_id"] = task.id
    elif isinstance(task, WebMasterTask):
        evaluation_kwargs["web_master_task_id"] = task.id
    else:
        raise ValueError("Unsupported task type")

    evaluation = TaskEvaluation(**evaluation_kwargs)
    db.add(evaluation)


def validate_date_range(start_date, end_date, start_label, end_label):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail=f"'{start_label}' must be ≤ '{end_label}'",
        )


async def check_creative_approaches(task: DesignerTask) -> None:
    if not task.creatives:
        return

    for creative in task.creatives:
        if not creative.approaches or len(creative.approaches) == 0:
            raise HTTPException(
                status_code=409,
                detail=f"Creative {creative.id} must have approaches field filled before sending task on review",
            )


async def check_media_files_for_review(task: DesignerTask) -> None:
    if task.is_operational:
        return

    if task.media_files:
        return

    if task.creatives:
        for creative in task.creatives:
            if creative.media_files:
                return

    raise HTTPException(status_code=409, detail="You must attach one media file before send task on review")


async def check_task_ready_for_review(task: DesignerTask) -> None:
    await check_media_files_for_review(task)
    await check_creative_approaches(task)
