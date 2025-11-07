from datetime import date, datetime, time, timezone

import pycountry
import structlog
from fastapi import HTTPException
from sqlalchemy import Integer, cast, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.models import (
    Celebrity,
    Creative,
    DesignersTeamMembers,
    DesignerTask,
    DesignerTaskDifficulty,
    DesignerTaskEdit,
    DesignerTaskHistory,
    Geo,
    Language,
    MediaBuyersTeam,
    MediaBuyersTeamMembers,
    TaskNote,
    User,
)
from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.enums.task_status import (
    DesignerTaskStatus,
)
from app.schemas.enums.task_type import DesignerTaskTypeEnum
from app.schemas.enums.user import UserRole

logger = structlog.get_logger(__name__)


async def create_task_history(db, task_id: int, buyer_id: int):
    task_status = await db.scalar(select(DesignerTask.task_status).where(DesignerTask.id == task_id))

    stmt = insert(DesignerTaskHistory).values(
        task_id=task_id, buyer_id=buyer_id, event="create", event_info=task_status.name
    )

    await db.execute(stmt)
    await db.commit()


async def build_designer_task_filters(  # noqa: C901 PLR0912 PLR0915
    db,
    user: User,
    task_type: DesignerTaskTypeEnum | None,
    task_statuses: list[DesignerTaskStatus] | None,
    created_from: date | None,
    created_to: date | None,
    is_need_to_assign: bool | None,
    is_media_buyers_teams: bool | None,
    is_high_priority: bool | None,
    created_by_id: list[int] | None,
    buyer_team_ids: list[int] | None,
    assigned_to_id: list[int] | None,
    title: str | None = None,
    is_operational: bool | None = None,
    is_deleted: bool | None = None,
    difficulty_ids: list[int] | None = None,
    designer_team_ids: list[int] | None = None,
    vertical: VerticalType | None = None,
    geo_codes: list[int] | None = None,
    ad_name: str | None = None,
) -> list:
    filters = []

    if task_type:
        filters.append(DesignerTask.task_type == task_type)

    if task_statuses:
        filters.append(DesignerTask.task_status.in_(task_statuses))

    if created_from:
        filters.append(DesignerTask.created_at >= datetime.combine(created_from, time.min))

    if created_to:
        filters.append(DesignerTask.created_at <= datetime.combine(created_to, time.max))

    if is_high_priority:
        filters.append(DesignerTask.is_high_priority.is_(True))

    if is_need_to_assign:
        filters.append(DesignerTask.assigned_to_id.is_(None))

    if title:
        filters.append(DesignerTask.title.ilike(f"%{title}%"))

    if user.role == UserRole.media_buyer:
        filters.append(DesignerTask.created_by_id == user.id)
    elif user.role == UserRole.designer:
        filters.append(DesignerTask.assigned_to_id == user.id)
    elif user.role == UserRole.lead_media_buyer:
        if getattr(user.media_buyer, "allow_view_team_tasks", False):
            team_ids = select(MediaBuyersTeam.id).where(MediaBuyersTeam.lead_id == user.id)
            team_members = select(MediaBuyersTeamMembers.media_buyer_id).where(
                MediaBuyersTeamMembers.team_id.in_(team_ids)
            )
            filters.append(DesignerTask.created_by_id.in_(team_members))
        else:
            filters.append(DesignerTask.created_by_id == user.id)

    if is_media_buyers_teams and user.role == UserRole.lead_designer:
        team_members_stmt = (
            select(MediaBuyersTeamMembers.media_buyer_id)
            .join(MediaBuyersTeam, MediaBuyersTeam.id == MediaBuyersTeamMembers.team_id)
            .where(MediaBuyersTeam.responsible_designer == user.id)
        )
        team_member_ids = await db.scalars(team_members_stmt)
        filters.append(DesignerTask.created_by_id.in_(list(team_member_ids)))

    if user.role not in (UserRole.media_buyer, UserRole.lead_media_buyer, UserRole.admin):
        filters.append(DesignerTask.task_status != DesignerTaskStatus.DRAFT)

    if user.role not in (UserRole.lead_designer, UserRole.admin, UserRole.designer):
        filters.append(DesignerTask.is_operational.is_(False))

    if created_by_id:
        filters.append(DesignerTask.created_by_id.in_(created_by_id))

    if is_operational:
        filters.append(DesignerTask.is_operational.is_(True))

    if designer_team_ids:
        subq_designers = (
            select(DesignersTeamMembers.designer_id)
            .where(DesignersTeamMembers.team_id.in_(designer_team_ids))
            .scalar_subquery()
        )
        filters.append(DesignerTask.assigned_to_id.in_(subq_designers))

    if buyer_team_ids:
        filters.append(DesignerTask.buyer_team_id.in_(buyer_team_ids))

    if assigned_to_id:
        filters.append(DesignerTask.assigned_to_id.in_(assigned_to_id))

    if is_deleted:
        filters.append(DesignerTask.is_deleted.is_(True))
    else:
        filters.append(DesignerTask.is_deleted.is_(False))

    if difficulty_ids:
        subq = (
            select(DesignerTaskDifficulty.task_id)
            .where(DesignerTaskDifficulty.difficulty_id.in_(difficulty_ids))
            .scalar_subquery()
        )
        filters.append(DesignerTask.id.in_(subq))

    if vertical:
        subq = select(MediaBuyersTeam.id).where(MediaBuyersTeam.vertical == vertical).scalar_subquery()
        filters.append(DesignerTask.buyer_team_id.in_(subq))

    if geo_codes:
        filters.append(DesignerTask.geo_id.in_(geo_codes))

    if ad_name:
        subq = select(Creative.task_id).where(Creative.ad_name.ilike(f"%{ad_name}%")).scalar_subquery()
        filters.append(DesignerTask.id.in_(subq))

    return filters


async def get_task_by_id(db, task_id: int):
    if task := await db.scalar(
        select(DesignerTask).where(DesignerTask.id == task_id, DesignerTask.is_deleted.is_(False))
    ):
        return task
    raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")


async def get_team_by_id(db, user: User):
    if team_id := await db.scalar(
        select(MediaBuyersTeamMembers.team_id).where(MediaBuyersTeamMembers.media_buyer_id == user.id)
    ):
        return team_id
    raise HTTPException(status_code=404, detail="Team ID not found for user")


async def get_next_designer_task_seq(
    db: AsyncSession,
    team_id: int,
    team_prefix: str,
    start_id: int,
) -> int:
    last_part = func.reverse(func.split_part(func.reverse(DesignerTask.title), ".", 1))

    max_seq_sql = func.max(cast(last_part, Integer))

    max_seq_query = (
        select(max_seq_sql)
        .where(DesignerTask.buyer_team_id == team_id)
        .where(DesignerTask.task_status != DesignerTaskStatus.DRAFT)
        .where(DesignerTask.title.like(f"{team_prefix}.%"))
    )

    current_max: int | None = await db.scalar(max_seq_query)

    if current_max is None or current_max < start_id:
        return start_id

    return current_max + 1


async def validate_buyer_edit_permission(task: DesignerTask, current_user: User):
    if task.task_status != DesignerTaskStatus.UNDER_BUYER_REVIEW:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Task is not under buyer review")

    if current_user.role == UserRole.admin:
        return

    if task.created_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't edit this task")


async def ensure_no_unsolved_edit_request(db, task_id: int):
    if await db.scalar(
        select(DesignerTaskEdit).where(DesignerTaskEdit.task_id == task_id, DesignerTaskEdit.solved_at.is_(None))
    ):
        raise HTTPException(status_code=409, detail="Task already has an unsolved edit request")


async def check_task_permissions(
    task: DesignerTask,
    user: User,
):
    if user.role == UserRole.media_buyer and task.created_by_id != user.id:
        raise HTTPException(status_code=403, detail="You did not create this task")

    if user.role == UserRole.designer and task.assigned_to_id != user.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this task")


async def validate_edit_exists_and_unsolved(edit: DesignerTaskEdit):
    if not edit:
        raise HTTPException(status_code=404, detail="Edit not found")

    if edit.solved_at is not None:
        raise HTTPException(status_code=409, detail="Edit already solved")


async def ensure_task_is_draft(task_status: DesignerTaskStatus):
    if task_status != DesignerTaskStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Task must be in draft status.")


async def check_filter_permissions(
    task_statuses: list[DesignerTaskStatus],
    user: User,
    is_media_buyers_teams: bool = False,
    is_need_to_assign: bool = False,
    created_by_id: list[int] | None = None,
    buyer_team_ids: list[int] | None = None,
    assigned_to_id: list[int] | None = None,
    is_operational: bool | None = None,
    is_deleted: bool | None = None,
    difficulty_ids: list[int] | None = None,
):
    if user.role != UserRole.lead_designer and (is_media_buyers_teams or is_need_to_assign):
        raise HTTPException(status_code=400, detail="Only lead designers can filter by media buyer teams or assignment")

    if (
        user.role not in (UserRole.media_buyer, UserRole.admin, UserRole.lead_media_buyer)
        and task_statuses
        and DesignerTaskStatus.DRAFT in task_statuses
    ):
        raise HTTPException(
            status_code=400, detail="Only media buyers, lead media buyers, or admins can filter by DRAFT tasks"
        )

    if user.role in (UserRole.designer, UserRole.media_buyer) and created_by_id:
        raise HTTPException(status_code=400, detail="You don't have enough permissions for filter 'created_by_id'")

    if user.role in (UserRole.designer, UserRole.media_buyer) and buyer_team_ids:
        raise HTTPException(
            status_code=400, detail="You don't have enough permissions for filter 'tasks_by_buyer_team_id'"
        )

    if user.role in (UserRole.designer, UserRole.media_buyer) and assigned_to_id:
        raise HTTPException(status_code=400, detail="You don't have enough permissions for filter 'assigned_to_id'")

    if user.role not in (UserRole.lead_designer, UserRole.admin, UserRole.designer) and is_operational:
        raise HTTPException(status_code=400, detail="You don't have enough permissions for filter 'is_operational'")

    if user.role != UserRole.admin and is_deleted:
        raise HTTPException(
            status_code=400,
            detail="Filter 'is_deleted' is available only for admin",
        )
    if user.role not in (UserRole.designer, UserRole.lead_designer, UserRole.admin) and difficulty_ids:
        raise HTTPException(status_code=400, detail="Filter 'difficulty_ids' is available only for designers")


async def validate_date_range(
    created_from: date | None = None,
    created_to: date | None = None,
) -> None:
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=400,
            detail="'created_from' must be ≤ 'created_to'",
        )


def restrict_media_files(task: DesignerTask, user: User) -> None:
    if user.role in (UserRole.designer, UserRole.lead_designer, UserRole.admin):
        return
    if user.role in (UserRole.media_buyer, UserRole.lead_media_buyer) and task.task_status in (
        DesignerTaskStatus.UNDER_BUYER_REVIEW,
        DesignerTaskStatus.COMPLETED,
    ):
        return
    task.media_files = [f for f in task.media_files if getattr(f, "is_description", False)]


def restrict_task_notes(task: DesignerTask, user: User) -> None:
    if user.role in (UserRole.lead_designer, UserRole.admin):
        return

    if user.role in (UserRole.media_buyer, UserRole.lead_media_buyer):
        task.notes = [note for note in task.notes if note.author_id == user.id]
    else:
        task.notes = []


async def get_task_note(
    session: AsyncSession,
    task_id: int,
    user: User,
) -> str | None:
    with session.no_autoflush:
        if user.role == UserRole.admin:
            stmt = (
                select(TaskNote.content, TaskNote.is_team_note, User.username)
                .outerjoin(User, User.id == TaskNote.author_id)
                .where(TaskNote.designer_task_id == task_id)
            )
            rows = (await session.execute(stmt)).all()
            notes = [
                {
                    "user": "lead_designer" if is_team else (username or "unknown"),
                    "note": content,
                }
                for content, is_team, username in rows
            ]
            return notes

        if user.role == UserRole.lead_designer:
            stmt = select(TaskNote.content).where(
                TaskNote.designer_task_id == task_id,
                TaskNote.is_team_note.is_(True),
            )
        else:
            stmt = select(TaskNote.content).where(
                TaskNote.designer_task_id == task_id,
                TaskNote.author_id == user.id,
                TaskNote.is_team_note.is_(False),
            )

        return await session.scalar(stmt)


_END_STATUSES = {
    DesignerTaskStatus.UNDER_TL_REVIEW.value,
    DesignerTaskStatus.UNDER_BUYER_REVIEW.value,
}


def _to_utc(dt):
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def calc_time_spent_seconds(db: AsyncSession, task_id: int) -> int:
    with db.no_autoflush:
        rows = (
            await db.execute(
                select(DesignerTaskHistory.changed_at, DesignerTaskHistory.event_info)
                .where(
                    DesignerTaskHistory.task_id == task_id,
                    DesignerTaskHistory.event == "status",
                )
                .order_by(DesignerTaskHistory.changed_at)
            )
        ).all()

    total = 0
    current_start = None

    for changed_at, status in rows:
        changed_at = _to_utc(changed_at)

        if status == DesignerTaskStatus.IN_PROGRESS.value:
            current_start = changed_at
        elif status in _END_STATUSES and current_start:
            total += int((changed_at - current_start).total_seconds())
            current_start = None

    if current_start:
        total += int((datetime.now(timezone.utc) - current_start).total_seconds())

    return total


def resolve_geo(code: str) -> tuple[str, str]:
    code = code.upper()
    if len(code) != 2:
        raise HTTPException(400, "Geo code must be 2 letters")
    country = pycountry.countries.get(alpha_2=code)
    if not country:
        raise HTTPException(400, "Invalid geo code")
    return code, country.name


async def get_geo_by_id(db: AsyncSession, geo_id: int) -> Geo:
    geo = await db.scalar(select(Geo).where(Geo.id == geo_id))
    if geo:
        return geo
    raise HTTPException(status_code=404, detail=f"Geo with ID {geo_id} not found")


async def get_language_by_id(db: AsyncSession, language_id: int) -> Language:
    language = await db.scalar(select(Language).where(Language.id == language_id))
    if language:
        return language
    raise HTTPException(status_code=404, detail=f"Language with ID {language_id} not found")


async def get_celebrity_by_id(db: AsyncSession, celebrity_id: int) -> Celebrity:
    celebrity = await db.scalar(select(Celebrity).where(Celebrity.id == celebrity_id))
    if celebrity:
        return celebrity
    raise HTTPException(status_code=404, detail=f"Celebrity with ID {celebrity_id} not found")


def get_task_creation_description(task_creatives: list, username: str) -> str:
    creatives_count = len(task_creatives) if task_creatives else 0
    if creatives_count > 0:
        return f"Task with {creatives_count} creatives created by {username}"
    return f"Task created by {username}"


async def check_task_status(
    task,
    required_status: str | None = None,
    forbidden_status: str | None = None,
    allowed_statuses: list | None = None,
    detail: str = "Task status check failed",
):
    from fastapi import HTTPException, status

    if required_status and task.task_status.value != required_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{detail}. Required status: {required_status}, current: {task.task_status.value}",
        )

    if forbidden_status and task.task_status.value == forbidden_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{detail}. Forbidden status: {forbidden_status}, current: {task.task_status.value}",
        )

    if allowed_statuses and task.task_status.value not in [s.value for s in allowed_statuses]:
        allowed_values = [s.value for s in allowed_statuses]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{detail}. Allowed statuses: {allowed_values}, current: {task.task_status.value}",
        )


async def ensure_task_was_updated(updated_task_id: int, detail: str = "Task update failed"):
    from fastapi import HTTPException, status

    if updated_task_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


async def ensure_can_edit_priority(user, task, update_data: dict, db):
    from fastapi import HTTPException, status

    from app.schemas.enums.user import UserRole

    if "is_high_priority" in update_data:
        if user.role not in [UserRole.lead_media_buyer, UserRole.media_buyer]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only media buyers can change task priority"
            )
