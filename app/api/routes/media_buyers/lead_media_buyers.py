from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query

from app.dependecies.auth import AuthenticateMainRoles
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import (
    User,
)
from app.repository.database.base import DatabaseRepository
from app.schemas.media_buyer_team import MediaBuyerShortResponseSchema

logger = structlog.get_logger(__name__)

lead_media_buyer_router = APIRouter(
    prefix="/lead_media_buyer",
    tags=["Lead Media Buyer"],
)


@lead_media_buyer_router.get("/media_buyers_by_team", response_model=list[MediaBuyerShortResponseSchema])
async def get_media_buyers_by_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: list[int] = Query(..., description="ID Team"),
    current_user: User = Depends(AuthenticateMainRoles()),
):
    return await db_repo.lead_media_buyer.get_media_buyers_by_team(team_id=team_id)
