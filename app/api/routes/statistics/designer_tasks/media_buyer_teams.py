from typing import Annotated, List, Literal

from fastapi import APIRouter, Depends, Query

from app.dependecies.auth import AuthenticateLeadDesigner
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.repository.media_buyers.media_buyer_team.utils import sort_vertical_stats
from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.media_buyer_team import MediaBuyerVerticalStatistic
from app.schemas.pagination import PaginationResponse

router = APIRouter()


@router.get("/media_buyer/teams", response_model=PaginationResponse[MediaBuyerVerticalStatistic])
async def get_media_buyer_teams_statistics(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateLeadDesigner()),
    team_id: int | None = Query(None, description="Team ID to filter media buyer teams"),
    vertical: list[VerticalType] | None = Query(
        None,
        description="Filter by vertical. Repeat param for several",
    ),
    order_by: Literal[
        "vertical",
        "waiting_to_start",
        "in_progress",
        "requested_changes",
        "under_tl_review",
        "under_buyer_review",
    ]
    | None = Query(
        None,
        description="Sort by field",
    ),
    order_direction: Literal["asc", "desc"] = Query("desc"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    raw_stats: List[dict] = await db_repo.media_buyer_team.get_media_buyer_teams_task_counts(
        team_id=team_id,
        vertical=vertical,
    )

    raw_stats = sort_vertical_stats(raw_stats, order_by, order_direction)

    total = len(raw_stats)
    page_raw = raw_stats[offset : offset + limit]

    page_items = [MediaBuyerVerticalStatistic(**row) for row in page_raw]

    return PaginationResponse.create(
        items=page_items,
        total=total,
        limit=limit,
        offset=offset,
    )
