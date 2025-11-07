from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import ORJSONResponse

from app.dependecies.auth import AuthenticateMainRoles
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.repository.media_buyers.media_buyer_team.utils import sort_buyer_stats
from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.media_buyer import MediaBuyerStatisticsSchema
from app.schemas.pagination import PaginationResponse

router = APIRouter()


@router.get("/buyers_statistics", response_model=PaginationResponse[MediaBuyerStatisticsSchema])
async def get_buyers_statistics(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int = Query(None, description="Filter by team ID"),
    vertical: list[VerticalType] = Query(None, description="Filter by vertical. Repeat param for several"),
    start_date: date = Query(None, description="Start date for task creation"),
    end_date: date = Query(None, description="End date for task creation"),
    limit: int = Query(10, ge=1, le=100, description="Limit of buyers per page"),
    offset: int = Query(0, ge=0, description="Offset of buyers"),
    order_by: Literal["username", "tasks_created", "tasks_completed", "mean_rating"] | None = Query(
        None,
        description="Sorting: username | tasks_created | tasks_completed | mean_rating",
    ),
    order_direction: Literal["asc", "desc"] = Query("desc"),
    current_user: User = Depends(AuthenticateMainRoles()),
):
    items = await db_repo.media_buyer_team.get_buyer_statistics(
        team_id=team_id,
        vertical=vertical,
        start_date=start_date,
        end_date=end_date,
        limit=10_000,
        offset=0,
    )

    items = sort_buyer_stats(items, order_by, order_direction)

    total_tasks_created = sum(i.tasks_created for i in items)
    total_tasks_completed = sum(i.tasks_completed for i in items)

    paged_items = items[offset : offset + limit]

    resp = PaginationResponse.create(
        items=paged_items,
        total=len(items),
        limit=limit,
        offset=offset,
    ).model_dump()

    resp["total_tasks_created"] = total_tasks_created
    resp["total_tasks_completed"] = total_tasks_completed

    return ORJSONResponse(content=resp)
