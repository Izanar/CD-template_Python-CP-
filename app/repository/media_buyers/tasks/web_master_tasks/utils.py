from datetime import date, datetime, time

from fastapi import HTTPException
from sqlalchemy import func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from starlette import status

from app.models import (
    MediaBuyer,
    MediaBuyersTeam,
    MediaBuyersTeamMembers,
    User,
    WebMasterDifficultyLevel,
    WebMasterTask,
    WebMasterTaskDifficulty,
    WebMasterTaskEdit,
    WebMasterTaskHistory,
    WebMasterTaskType,
)
from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.enums.task_status import WebMasterTaskStatus
from app.schemas.enums.user import UserRole
from app.schemas.enums.web_master_task import WebMasterProjectType
from app.schemas.media_buyer import WebMasterTaskCreateSchema


async def build_web_master_task_filters(  # noqa: C901 PLR0912
    db,
    user: User,
    task_type: int | None,
    task_statuses: WebMasterTaskStatus | None,
    created_from: date | None,
    created_to: date | None,
    is_need_to_assign: bool | None,
    is_media_buyers_teams: bool | None,
    is_high_priority: bool | None,
    created_by_id: int | None,
    buyer_team_id: int | None,
    assigned_to_id: int | None,
    title: str | None = None,
    geo_codes: list[int] | None = None,
    vertical: VerticalType | None = None,
    funnel_ids: list[int] | None = None,
    celebrity_ids: list[int] | None = None,
    site_name_ids: list[int] | None = None,
    is_deleted: bool | None = None,
) -> list:
    filters = []

    if task_type:
        filters.append(WebMasterTask.task_type_id == task_type)

    if task_statuses:
        filters.append(WebMasterTask.task_status.in_(task_statuses))

    if created_from:
        filters.append(WebMasterTask.created_at >= datetime.combine(created_from, time.min))

    if created_to:
        filters.append(WebMasterTask.created_at <= datetime.combine(created_to, time.max))

    if is_high_priority:
        filters.append(WebMasterTask.is_high_priority.is_(True))

    if is_need_to_assign:
        filters.append(WebMasterTask.assigned_to_id.is_(None))

    if title:
        filters.append(WebMasterTask.title.ilike(f"%{title}%"))

    if vertical:
        subq = select(MediaBuyersTeam.id).where(MediaBuyersTeam.vertical == vertical).scalar_subquery()
        filters.append(WebMasterTask.buyer_team_id.in_(subq))

    if geo_codes:
        filters.append(WebMasterTask.geo_id.in_(geo_codes))

    if funnel_ids:
        filters.append(WebMasterTask.funnel_id.in_(funnel_ids))

    if site_name_ids:
        filters.append(WebMasterTask.site_name_id.in_(site_name_ids))

    if celebrity_ids:
        filters.append(WebMasterTask.celebrity_id.in_(celebrity_ids))

    match user.role:
        case UserRole.media_buyer:
            filters.append(WebMasterTask.created_by_id == user.id)

        case UserRole.web_master:
            filters.append(WebMasterTask.assigned_to_id == user.id)

        case UserRole.lead_media_buyer:
            team_ids = select(MediaBuyersTeam.id).where(MediaBuyersTeam.lead_id == user.id)
            team_members = select(MediaBuyersTeamMembers.media_buyer_id).where(
                MediaBuyersTeamMembers.team_id.in_(team_ids)
            )
            filters.append(WebMasterTask.created_by_id.in_(team_members))

    if is_media_buyers_teams and user.role == UserRole.lead_web_master:
        team_members_stmt = (
            select(MediaBuyersTeamMembers.media_buyer_id)
            .join(MediaBuyersTeam, MediaBuyersTeam.id == MediaBuyersTeamMembers.team_id)
            .where(MediaBuyersTeam.responsible_designer == user.id)
        )
        team_member_ids = await db.scalars(team_members_stmt)
        filters.append(WebMasterTask.created_by_id.in_(list(team_member_ids)))

    if user.role not in (UserRole.media_buyer, UserRole.lead_media_buyer):
        filters.append(WebMasterTask.task_status != WebMasterTaskStatus.DRAFT)

    if created_by_id:
        filters.append(WebMasterTask.created_by_id == created_by_id)

    if buyer_team_id:
        filters.append(WebMasterTask.buyer_team_id == buyer_team_id)

    if assigned_to_id:
        filters.append(WebMasterTask.assigned_to_id == assigned_to_id)

    if is_deleted:
        filters.append(WebMasterTask.is_deleted.is_(True))
    else:
        filters.append(WebMasterTask.is_deleted.is_(False))

    return filters


async def create_task_history(db, task_id: int, buyer_id: int):
    task_status = await db.scalar(select(WebMasterTask.task_status).where(WebMasterTask.id == task_id))

    stmt = insert(WebMasterTaskHistory).values(
        task_id=task_id, buyer_id=buyer_id, event="create", event_info=task_status.name
    )

    await db.execute(stmt)
    await db.commit()


async def check_task_type_exists(db, task_type_id: int):
    task_type = await db.scalar(select(WebMasterTaskType).where(WebMasterTaskType.id == task_type_id))
    if task_type is None:
        raise HTTPException(404, "Task type does not exist")

    return task_type


async def get_team_by_id(db, user: User):
    if team_id := await db.scalar(
        select(MediaBuyersTeamMembers.team_id).where(MediaBuyersTeamMembers.media_buyer_id == user.id)
    ):
        return team_id
    raise HTTPException(status_code=404, detail="Team ID not found for user")


async def ensure_task_is_draft(task_status: WebMasterTaskStatus):
    if task_status != WebMasterTaskStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Task must be in draft status.")


async def get_task_by_id(db, task_id: int):
    if task := await db.scalar(select(WebMasterTask).where(WebMasterTask.id == task_id)):
        return task
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")


async def check_filter_permissions(
    user: User,
    is_media_buyers_teams: bool = False,
    is_need_to_assign: bool = False,
    task_statuses: list[WebMasterTaskStatus] | None = None,
    created_by_id: int | None = None,
    buyer_team_id: int | None = None,
    assigned_to_id: int | None = None,
):
    if user.role != UserRole.lead_web_master and (is_media_buyers_teams or is_need_to_assign):
        raise HTTPException(
            status_code=400, detail="Only lead web masters can filter by media buyer teams or assignment"
        )

    if (
        user.role not in (UserRole.media_buyer, UserRole.admin, UserRole.lead_media_buyer)
        and task_statuses
        and WebMasterTaskStatus.DRAFT in task_statuses
    ):
        raise HTTPException(
            status_code=400, detail="Only media buyers, lead media buyers, or admins can filter by DRAFT tasks"
        )

    if user.role in (UserRole.web_master, UserRole.media_buyer) and created_by_id:
        raise HTTPException(status_code=400, detail="You don't have enough permissions for filter 'created_by_id'")

    if user.role in (UserRole.web_master, UserRole.media_buyer) and buyer_team_id:
        raise HTTPException(
            status_code=400, detail="You don't have enough permissions for filter 'tasks_by_buyer_team_id'"
        )

    if user.role in (UserRole.web_master, UserRole.media_buyer) and assigned_to_id:
        raise HTTPException(status_code=400, detail="You don't have enough permissions for filter 'assigned_to_id'")


async def validate_date_range(
    created_from: date | None = None,
    created_to: date | None = None,
) -> None:
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=400,
            detail="'created_from' must be ≤ 'created_to'",
        )


async def check_task_permissions(
    task: WebMasterTask,
    user: User,
):
    if user.role == UserRole.media_buyer and task.created_by_id != user.id:
        raise HTTPException(status_code=403, detail="You did not create this task")

    if user.role == UserRole.web_master and task.assigned_to_id != user.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this task")


async def get_next_web_master_task_seq(db, team_id: int):
    seq_query = (
        select(func.count())
        .select_from(WebMasterTask)
        .join(MediaBuyer, WebMasterTask.created_by_id == MediaBuyer.id)
        .join(
            MediaBuyersTeamMembers,
            MediaBuyersTeamMembers.media_buyer_id == MediaBuyer.id,
        )
        .where(MediaBuyersTeamMembers.team_id == team_id)
    )
    count = await db.scalar(seq_query) or 0
    return count + 1


async def validate_edit_exists_and_unsolved(edit: WebMasterTaskEdit):
    if not edit:
        raise HTTPException(status_code=404, detail="Edit not found")

    if edit.solved_at is not None:
        raise HTTPException(status_code=409, detail="Edit already solved")


async def ensure_no_unsolved_edit_request(db, task_id: int):
    if await db.scalar(
        select(WebMasterTaskEdit).where(WebMasterTaskEdit.task_id == task_id, WebMasterTaskEdit.solved_at.is_(None))
    ):
        raise HTTPException(status_code=409, detail="There is already an edit request in progress")


async def validate_buyer_edit_permission(task: WebMasterTask, current_user: User):
    if task.task_status != WebMasterTaskStatus.UNDER_BUYER_REVIEW:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Task is not under buyer review")

    if task.created_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't edit this task")


def validate_webmaster_task_primitives(task: WebMasterTaskCreateSchema) -> None:
    always_required = ["geo_id"]
    extra_required = []

    if task.project_type not in {
        WebMasterProjectType.WHITE,
        WebMasterProjectType.CAMPAIGN_WHITE,
    }:
        extra_required = ["funnel_id", "site_name_id", "celebrity_id"]

    missing = [field for field in (always_required + extra_required) if getattr(task, field) is None]

    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing {', '.join(missing)} for project type {task.project_type.value}",
        )


def ensure_lead(update_data: dict, user) -> None:
    if {"geo_id", "funnel_id", "site_name_id", "celebrity_id"} & update_data.keys() and user.role not in (
        UserRole.admin,
        UserRole.lead_web_master,
    ):
        raise HTTPException(403, "Only Lead Web‑Master may update geo / funnel / site / celebrity.")


_TYPE_TO_DIFF = {
    "create": "Medium",
    "edit": "Low",
    "duplicate": "Low",
    "transfer": "Low",
}


async def add_default_difficulty_if_needed(db, task_id: int, task_type_name: str) -> None:
    diff_name = _TYPE_TO_DIFF.get(task_type_name.lower())
    if not diff_name:
        return
    print(diff_name)
    diff_id = await db.scalar(select(WebMasterDifficultyLevel.id).where(WebMasterDifficultyLevel.name == diff_name))
    if not diff_id:
        return

    await db.execute(
        pg_insert(WebMasterTaskDifficulty).values(task_id=task_id, difficulty_id=diff_id).on_conflict_do_nothing()
    )
