from typing import Annotated

import structlog
from fastapi import APIRouter, Depends

from app.dependecies.auth import AuthenticateAdmin
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import MediaBuyersTeam, User
from app.repository.database.base import DatabaseRepository
from app.schemas.media_buyer_team import (
    AddMediaBuyerLeadSchema,
    AddResponsibleWebMasterSchema,
    CreateMediaBuyerTeamSchema,
    MediaBuyerTeamDetailResponseSchema,
    UpdateMediaBuyerTeamSchema,
)
from app.schemas.message import MessageSchema

admin_media_buyers_team_router = APIRouter(
    prefix="/admin/media_buyers_team",
    tags=["Admin"],
)

logger = structlog.get_logger()


@admin_media_buyers_team_router.post(
    "/create",
    response_model=MediaBuyerTeamDetailResponseSchema,
    status_code=200,
)
async def create_media_buyer_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team: CreateMediaBuyerTeamSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    """Create a media buyer team."""
    return await db_repo.admin_media_buyer_team.create_team(team_info=team)


@admin_media_buyers_team_router.post(
    "/add_responsible_designer", status_code=200, response_model=MediaBuyerTeamDetailResponseSchema
)
async def add_responsible_designer(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int,
    responsible_designer_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_media_buyer_team.add_responsible_designer(
        team_id=team_id,
        responsible_designer_id=responsible_designer_id,
    )


@admin_media_buyers_team_router.delete(
    "/remove_responsible_designer",
    response_model=MessageSchema,
    status_code=200,
)
async def remove_responsible_designer(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int,
    responsible_designer_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
) -> MessageSchema:
    return await db_repo.admin_media_buyer_team.remove_responsible_designer(
        team_id=team_id, responsible_designer_id=responsible_designer_id
    )


@admin_media_buyers_team_router.post(
    "/add_responsible_web_master", status_code=200, response_model=MediaBuyerTeamDetailResponseSchema
)
async def add_responsible_web_master(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    data: AddResponsibleWebMasterSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_media_buyer_team.add_responsible_web_master(
        responsible_web_master_id=data.responsible_web_master_id, team_id=data.team_id
    )


@admin_media_buyers_team_router.delete(
    "/remove_responsible_web_master",
    response_model=MessageSchema,
    status_code=200,
)
async def remove_responsible_web_master(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    data: AddResponsibleWebMasterSchema,
    current_user: User = Depends(AuthenticateAdmin()),
) -> MessageSchema:
    return await db_repo.admin_media_buyer_team.remove_responsible_web_master(team_id=data.team_id)


@admin_media_buyers_team_router.patch(
    "/{team_id}/update",
    response_model=MediaBuyerTeamDetailResponseSchema,
    status_code=200,
)
async def update_media_buyer_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int,
    data: UpdateMediaBuyerTeamSchema,
    current_user: User = Depends(AuthenticateAdmin()),
) -> MediaBuyersTeam:
    """Update a media buyer team."""
    return await db_repo.admin_media_buyer_team.update_team(
        team_id=team_id,
        data=data,
    )


@admin_media_buyers_team_router.delete(
    "/{team_id}/remove",
    response_model=MessageSchema,
    status_code=200,
)
async def delete_media_buyer_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
) -> MessageSchema:
    """Delete a media buyer team."""
    return await db_repo.admin_media_buyer_team.delete_team(team_id=team_id)


@admin_media_buyers_team_router.post(
    "/{team_id}/add_buyer",
    response_model=MediaBuyerTeamDetailResponseSchema,
    status_code=200,
)
async def add_buyer_to_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int,
    buyer_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
) -> MediaBuyersTeam:
    return await db_repo.admin_media_buyer_team.add_buyer_to_team(team_id=team_id, buyer_id=buyer_id)


@admin_media_buyers_team_router.delete(
    "/{team_id}/remove_buyer",
    response_model=MessageSchema,
    status_code=200,
)
async def remove_buyer_from_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int,
    buyer_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
) -> MessageSchema:
    return await db_repo.admin_media_buyer_team.remove_buyer_from_team(team_id=team_id, buyer_id=buyer_id)


@admin_media_buyers_team_router.post("/add_lead", response_model=MediaBuyerTeamDetailResponseSchema)
async def add_lead_to_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    data: AddMediaBuyerLeadSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_media_buyer_team.add_lead_media_buyer_to_team(
        team_id=data.team_id, lead_id=data.media_buyer_lead_id
    )


@admin_media_buyers_team_router.delete("/remove_lead", response_model=MessageSchema)
async def remove_lead_from_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int,
    lead_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_media_buyer_team.remove_lead_buyer_from_team(team_id=team_id, lead_id=lead_id)
