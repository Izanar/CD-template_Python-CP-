from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.routes.statistics.utils import (
    build_designer_points_statistics,
    build_designer_statistics,
    sort_designer_statistics,
)
from app.dependecies.auth import AuthenticateDesignerOrLead, AuthenticateLeadDesigner
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.designers.statistics import DesignerPointsStatistic, DesignerStatistic, OperationalTasksStatistic
from app.schemas.pagination import PaginationResponse

router = APIRouter()


@router.get("/designers", response_model=PaginationResponse[DesignerStatistic])
async def get_designers_statistic(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateLeadDesigner()),
    team_id: list[int] | None = Query(
        None,
        description="Team ID to filter designers by teamExample: ?team_id=1&team_id=3",
    ),
    order_by: Literal[
        "waiting_to_start",
        "in_progress",
        "requested_changes",
        "under_tl_review",
        "under_buyer_review",
        "completed",
        "username",
    ]
    | None = Query(
        None,
        description="Which status column to sort by "
        "(waiting_to_start | in_progress | requested_changes | under_tl_review | "
        "under_buyer_review | completed | username)",
    ),
    order_direction: Literal["asc", "desc"] = Query("desc", description="asc or desc"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset"),
):
    designers = await db_repo.designer.get_designers(team_id=team_id)

    stats = build_designer_statistics(designers)

    stats = sort_designer_statistics(stats, order_by, order_direction)

    total = len(stats)
    paged_stats = stats[offset : offset + limit]

    return PaginationResponse.create(
        items=paged_stats,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/designers/points", response_model=PaginationResponse[DesignerPointsStatistic])
async def get_designers_points(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateDesignerOrLead()),
    team_id: int | None = Query(
        None,
        description="Team ID to filter designers points by team",
    ),
    order_by: Literal["completed_tasks", "total_points", "mean_rating", "username"] = Query(
        "total_points", description="Field to sort by (completed_tasks | total_points | mean_rating | username)"
    ),
    order_direction: Literal["asc", "desc"] = Query("desc", description="asc or desc"),
    created_from: date | None = Query(None, description="Created from (YYYY-MM-DD)"),
    created_to: date | None = Query(None, description="Created to (YYYY-MM-DD)"),
    completed_from: date | None = Query(None, description="Completed from this date (YYYY-MM-DD)"),
    completed_to: date | None = Query(None, description="Completed to this date (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset"),
):
    designer_data = await db_repo.designer.get_designers_completion_stats(
        team_id=team_id,
        created_from=created_from,
        created_to=created_to,
        completed_from=completed_from,
        completed_to=completed_to,
        order_by=order_by,
        order_direction=order_direction,
    )
    total = len(designer_data)
    paged_data = designer_data[offset : offset + limit]

    stats = build_designer_points_statistics(paged_data)

    return PaginationResponse.create(
        items=stats,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/designers/operational_tasks", response_model=OperationalTasksStatistic)
async def get_designers_operational_tasks_statistic(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateLeadDesigner()),
):
    return await db_repo.designer.get_media_buyer_teams_task_counts()
