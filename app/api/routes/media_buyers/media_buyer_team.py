from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query

from app.dependecies.auth import AuthenticateLeadMediaBuyer, AuthenticateMainRoles
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.media_buyer_team import (
    MediaBuyerTeamDetailResponseSchema,
)
from app.schemas.pagination import PaginationResponse

logger = structlog.get_logger()

media_buyer_team_router = APIRouter(
    prefix="/lead_media_buyer/team",
    tags=["Lead Media Buyer"],
)


@media_buyer_team_router.get(
    "/all",
    response_model=PaginationResponse[MediaBuyerTeamDetailResponseSchema],
    status_code=200,
)
async def get_media_buyer_teams(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateMainRoles()),
    limit: int = Query(10, ge=1, le=100, description="Limit of tasks per page"),
    offset: int = Query(0, ge=0, description="Offset of teams"),
    vertical: VerticalType | None = Query(
        None, description="Filter by vertical (e.g., crypto, gambling, nutra, google)"
    ),
):
    """Get all media buyer teams."""

    teams = await db_repo.media_buyer_team.get_media_buyer_teams(
        user=current_user,
        limit=limit,
        offset=offset,
        vertical=vertical,
    )

    tasks_schema = [MediaBuyerTeamDetailResponseSchema.model_validate(team, from_attributes=True) for team in teams]

    total = await db_repo.media_buyer_team.get_total_teams(vertical=vertical)

    return PaginationResponse.create(items=tasks_schema, total=total, limit=limit, offset=offset)


@media_buyer_team_router.get(
    "/{team_id}",
    response_model=MediaBuyerTeamDetailResponseSchema,
    status_code=200,
)
async def get_media_buyer_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int,
    current_user: User = Depends(AuthenticateLeadMediaBuyer()),
):
    """Get a media buyer team."""
    return await db_repo.media_buyer_team.get_media_buyer_team(
        team_id=team_id,
    )
