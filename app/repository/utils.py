from datetime import date
from typing import Any, List, Literal, Type, TypeVar

from fastapi import HTTPException
from sqlalchemy import BigInteger, Numeric, Select, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import (
    Base,
    Celebrity,
    Designer,
    DesignerTask,
    DesignerTaskDifficulty,
    DifficultyLevel,
    Funnel,
    Geo,
    MediaBuyer,
    MediaBuyersTeam,
    MediaBuyersTeamMembers,
    SiteName,
    TaskEvaluation,
    User,
    WebMaster,
)
from app.schemas.enums.task_status import DesignerTaskStatus, WebMasterTaskStatus

T = TypeVar("T", bound=Base)


def build_order_by(
    stmt: Select[Any],
    model: Type[T],
    order_by: str | None,
    order_direction: Literal["asc", "desc"] | None = None,
) -> Any:
    """Собрать ORDER BY для разных колонок, в т. ч. по приоритету и сложности."""

    desc_requested = order_direction == "desc"
    order_parts: list[Any] = []

    if order_by == "created_by_username":
        stmt = stmt.join(User, DesignerTask.created_by_id == User.id)
        col = User.username
        order_parts.append(col.desc() if desc_requested else col.asc())
        order_parts.append(model.created_at.desc())

    elif order_by == "assigned_to_username":
        stmt = stmt.outerjoin(Designer, DesignerTask.assigned_to_id == Designer.id).outerjoin(
            User, Designer.id == User.id
        )
        col = User.username
        order_parts.append(col.desc().nulls_last() if desc_requested else col.asc().nulls_last())
        order_parts.append(model.created_at.desc())

    elif order_by == "assigned_to_rating":
        stmt = stmt.outerjoin(Designer, DesignerTask.assigned_to_id == Designer.id)
        rating_subq = (
            select(func.avg(TaskEvaluation.rating))
            .where(TaskEvaluation.designer_task_id == DesignerTask.id)
            .correlate(DesignerTask)
            .scalar_subquery()
        )
        order_parts.append(rating_subq.desc().nulls_last() if desc_requested else rating_subq.asc().nulls_last())
        order_parts.append(model.created_at.desc())

    elif order_by == "vertical":
        stmt = stmt.outerjoin(MediaBuyersTeam, DesignerTask.buyer_team_id == MediaBuyersTeam.id)
        col = MediaBuyersTeam.vertical
        order_parts.append(col.desc().nulls_first() if desc_requested else col.asc().nulls_last())
        order_parts.append(model.created_at.desc())

    elif order_by == "is_high_priority":
        priority = case(
            (model.is_high_priority.is_(True), 0),
            (model.is_high_priority.is_(False), 1),
            else_=2,
        )
        order_parts.append(priority.desc().nullslast() if desc_requested else priority.asc().nullslast())
        order_parts.append(model.created_at.desc())

    elif order_by == "created_at":
        primary = model.created_at.desc() if not desc_requested else model.created_at.asc()
        order_parts.extend([primary, model.id.desc()])

    elif order_by == "task_status":
        status_order = case(
            *[(model.task_status == status.value.upper(), idx) for idx, status in enumerate(DesignerTaskStatus)],
            else_=len(DesignerTaskStatus),
        )
        order_parts.append(status_order.asc() if not desc_requested else status_order.desc())
        order_parts.append(model.created_at.desc())

    elif order_by == "title":
        text_part = func.regexp_replace(func.lower(model.title), r"\d+$", "")
        number_part = cast(func.substring(model.title, r"\d+$"), BigInteger)

        order_parts.append(text_part.asc() if not desc_requested else text_part.desc())

        order_parts.append(number_part.asc().nullslast() if not desc_requested else number_part.desc().nullsfirst())

        order_parts.append(model.created_at.desc())

    elif order_by == "deadline":
        col = model.deadline
        order_parts.append(col.desc().nullslast() if desc_requested else col.asc().nullslast())
        order_parts.append(model.created_at.desc())

    elif order_by == "difficulty_points":
        diff_points_subq = (
            select(func.max(DifficultyLevel.points))
            .join(DesignerTaskDifficulty, DesignerTaskDifficulty.difficulty_id == DifficultyLevel.id)
            .where(DesignerTaskDifficulty.task_id == model.id)
            .correlate(model)
            .scalar_subquery()
        )
        order_parts.append(diff_points_subq.asc() if not desc_requested else diff_points_subq.desc())
        order_parts.append(model.created_at.desc())

    elif order_by == "geo_code":
        geo_alias = aliased(Geo)
        stmt = stmt.outerjoin(geo_alias, DesignerTask.geo_id == geo_alias.id)

        order_parts.append(geo_alias.code.desc().nullslast() if desc_requested else geo_alias.code.asc().nullslast())
        order_parts.append(DesignerTask.created_at.desc())

    elif order_by:
        try:
            attr = getattr(model, order_by)
        except AttributeError:
            raise HTTPException(status_code=400, detail=f"Invalid order by field: {order_by}")
        order_parts.append(attr.asc() if not desc_requested else attr.desc())
        order_parts.append(model.created_at.desc())

    else:
        priority = case(
            (model.is_high_priority.is_(True), 0),
            (model.is_high_priority.is_(False), 1),
            else_=2,
        )
        order_parts.append(priority.desc().nullslast() if not desc_requested else priority.asc().nullslast())
        order_parts.append(model.created_at.desc())

    return stmt.order_by(*order_parts)


def validate_task_status(current_task_status: DesignerTaskStatus, allowed_task_statuses: tuple[DesignerTaskStatus]):
    if current_task_status not in allowed_task_statuses:
        raise HTTPException(
            status_code=409,
            detail=f"The task cannot be modified while its current "
            f"status is '{current_task_status.value}'. Allowed statuses for this action {allowed_task_statuses}",
        )


async def get_task_stats(
    db: AsyncSession,
    task_model,
    status_enum,
    team_id: int | None,
    vertical: list | None,
    start_date: date | None,
    end_date: date | None,
    limit: int,
    offset: int,
    include_user_info: bool = False,
) -> List[dict]:
    active_statuses = [status for status in status_enum if status is not status_enum.DRAFT]
    completed_status = status_enum.COMPLETED
    team_columns = [
        MediaBuyersTeam.id.label("team_id"),
        MediaBuyersTeam.name.label("team_name"),
        MediaBuyersTeam.vertical.label("vertical"),
    ]
    base_columns = [MediaBuyer.id.label("id")]
    user_columns = [User.username.label("name")] if include_user_info else []
    task_columns = [
        func.sum(case((task_model.task_status.in_(active_statuses), 1), else_=0)).label("tasks_created"),
        func.sum(case((task_model.task_status == completed_status, 1), else_=0)).label("tasks_completed"),
    ]

    median_rating_subquery = (
        select(
            task_model.created_by_id.label("creator_id"),
            func.round(cast(func.avg(TaskEvaluation.rating), Numeric), 2).label("mean_rating"),
        )
        .select_from(TaskEvaluation)
        .join(task_model, task_model.id == TaskEvaluation.designer_task_id)
        .where(TaskEvaluation.rating.is_not(None))
        .where(task_model.is_deleted.is_(False))
    )
    if start_date:
        median_rating_subquery = median_rating_subquery.where(task_model.created_at >= start_date)
    if end_date:
        median_rating_subquery = median_rating_subquery.where(task_model.created_at <= end_date)
    median_rating_subquery = median_rating_subquery.group_by(task_model.created_by_id).subquery()

    rating_column = [median_rating_subquery.c.mean_rating.label("mean_rating")]
    query = (
        select(*base_columns, *user_columns, *task_columns, *team_columns, *rating_column)
        .select_from(MediaBuyer)
        .outerjoin(MediaBuyersTeamMembers, MediaBuyersTeamMembers.media_buyer_id == MediaBuyer.id)
        .outerjoin(MediaBuyersTeam, MediaBuyersTeam.id == MediaBuyersTeamMembers.team_id)
        .outerjoin(median_rating_subquery, median_rating_subquery.c.creator_id == MediaBuyer.id)
    )

    if include_user_info:
        query = query.join(User, MediaBuyer.id == User.id)

    if team_id:
        query = query.filter(MediaBuyersTeamMembers.team_id == team_id)

    if vertical:
        query = query.filter(MediaBuyersTeam.vertical.in_(vertical))

    task_join_condition = (task_model.created_by_id == MediaBuyer.id) & task_model.is_deleted.is_(False)
    if start_date:
        task_join_condition &= task_model.created_at >= start_date
    if end_date:
        task_join_condition &= task_model.created_at <= end_date

    group_by_columns = [
        MediaBuyer.id,
        MediaBuyersTeam.id,
        MediaBuyersTeam.name,
        MediaBuyersTeam.vertical,
        *user_columns,
        median_rating_subquery.c.mean_rating,
    ]
    query = (
        query.outerjoin(task_model, task_join_condition)
        .group_by(*group_by_columns)
        .order_by(MediaBuyer.id)
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    return result.mappings().all()


def build_order_by_web_master_tasks(
    stmt: Select[Any],
    model: Type[T],
    order_by: str | None,
    order_direction: Literal["asc", "desc"] | None = None,
) -> Any:
    desc_requested = order_direction == "desc"
    order_parts: list[Any] = []

    if order_by == "created_by_username":
        stmt = stmt.join(User, model.created_by_id == User.id)
        col = User.username
        order_parts.append(col.desc() if desc_requested else col.asc())
        order_parts.append(model.created_at.desc())

    elif order_by == "assigned_to_username":
        stmt = stmt.outerjoin(WebMaster, model.assigned_to_id == WebMaster.id).outerjoin(
            User, WebMaster.user_id == User.id
        )
        col = User.username
        order_parts.append(col.desc().nulls_last() if desc_requested else col.asc().nulls_last())
        order_parts.append(model.created_at.desc())

    elif order_by == "vertical":
        stmt = stmt.outerjoin(MediaBuyersTeam, model.buyer_team_id == MediaBuyersTeam.id)
        col = MediaBuyersTeam.vertical
        order_parts.append(col.desc().nulls_last() if desc_requested else col.asc().nulls_last())
        order_parts.append(model.created_at.desc())

    elif order_by == "is_high_priority":
        priority = case(
            (model.is_high_priority.is_(True), 0),
            (model.is_high_priority.is_(False), 1),
            else_=2,
        )
        order_parts.append(priority.desc().nulls_last() if desc_requested else priority.asc().nulls_last())
        order_parts.append(model.created_at.desc())

    elif order_by == "created_at":
        primary = model.created_at.desc() if not desc_requested else model.created_at.asc()
        order_parts.extend([primary, model.id.desc()])

    elif order_by == "task_status":
        status_order = case(
            *[(model.task_status == status.value.upper(), idx) for idx, status in enumerate(WebMasterTaskStatus)],
            else_=len(WebMasterTaskStatus),
        )
        order_parts.append(status_order.asc() if not desc_requested else status_order.desc())
        order_parts.append(model.created_at.desc())

    elif order_by == "title":
        text_part = func.regexp_replace(func.lower(model.title), r"\d+$", "")
        number_part = cast(func.substring(model.title, r"\d+$"), BigInteger)
        order_parts.append(text_part.asc() if not desc_requested else text_part.desc())
        order_parts.append(number_part.asc().nulls_last() if not desc_requested else number_part.desc().nulls_last())
        order_parts.append(model.created_at.desc())

    elif order_by == "deadline":
        col = model.deadline
        order_parts.append(col.desc().nulls_last() if desc_requested else col.asc().nulls_last())
        order_parts.append(model.created_at.desc())

    elif order_by == "task_points":
        col = model.task_points
        order_parts.append(col.desc().nulls_last() if desc_requested else col.asc().nulls_last())
        order_parts.append(model.created_at.desc())

    elif order_by == "geo_code":
        geo_alias = aliased(Geo)
        stmt = stmt.outerjoin(geo_alias, model.geo_id == geo_alias.id)
        order_parts.append(geo_alias.code.desc().nulls_last() if desc_requested else geo_alias.code.asc().nulls_last())
        order_parts.append(model.created_at.desc())

    elif order_by == "funnel_name":
        funnel_alias = aliased(Funnel)
        stmt = stmt.outerjoin(funnel_alias, model.funnel_id == funnel_alias.id)
        order_parts.append(
            funnel_alias.name.desc().nulls_last() if desc_requested else funnel_alias.name.asc().nulls_last()
        )
        order_parts.append(model.created_at.desc())

    elif order_by == "site_name":
        site_name_alias = aliased(SiteName)
        stmt = stmt.outerjoin(site_name_alias, model.site_name_id == site_name_alias.id)
        order_parts.append(
            site_name_alias.name.desc().nulls_last() if desc_requested else site_name_alias.name.asc().nulls_last()
        )
        order_parts.append(model.created_at.desc())

    elif order_by == "celebrity_name":
        celebrity_alias = aliased(Celebrity)
        stmt = stmt.outerjoin(celebrity_alias, model.celebrity_id == celebrity_alias.id)
        order_parts.append(
            celebrity_alias.name.desc().nulls_last() if desc_requested else celebrity_alias.name.asc().nulls_last()
        )
        order_parts.append(model.created_at.desc())

    elif order_by:
        try:
            attr = getattr(model, order_by)
        except AttributeError:
            raise HTTPException(status_code=400, detail=f"Invalid order by field: {order_by}")
        order_parts.append(attr.asc().nulls_last() if not desc_requested else attr.desc().nulls_last())
        order_parts.append(model.created_at.desc())

    else:
        priority = case(
            (model.is_high_priority.is_(True), 0),
            (model.is_high_priority.is_(False), 1),
            else_=2,
        )
        order_parts.append(priority.desc().nulls_last() if not desc_requested else priority.asc().nulls_last())
        order_parts.append(model.created_at.desc())

    return stmt.order_by(*order_parts)
