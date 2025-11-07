from typing import Annotated

import structlog
from fastapi import APIRouter, Body, Depends, Path, Query

from app.dependecies.auth import AuthenticateAdmin
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.designers.designer_team_schema import (
    AddLeadDesignerTeamSchema,
    CreateDesignersTeamsPayload,
    DesignerTeamDetailsSchema,
    UpdateDesignerTeamSchema,
)
from app.schemas.message import MessageSchema

admin_designers_team_router = APIRouter(
    prefix="/admin/designers_team",
    tags=["Admin"],
)

logger = structlog.get_logger()


@admin_designers_team_router.post("/create", response_model=DesignerTeamDetailsSchema)
async def create_designers_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team: CreateDesignersTeamsPayload,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_designer_team.create_team(team_name=team.team_name)


@admin_designers_team_router.patch("/{team_id}/update", response_model=DesignerTeamDetailsSchema)
async def update_designers_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
    team_id: int = Path(..., description="ID команди дизайнерів"),
    update_data: UpdateDesignerTeamSchema = Body(..., description="Update data"),
):
    return await db_repo.admin_designer_team.update_team(team_id=team_id, team_name=update_data.name)


@admin_designers_team_router.delete("/{team_id}/remove", response_model=MessageSchema)
async def delete_designers_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
    team_id: int = Path(..., description="Team ID"),
):
    return await db_repo.admin_designer_team.delete_team(team_id=team_id)


@admin_designers_team_router.post("/{team_id}/add_designer", response_model=DesignerTeamDetailsSchema)
async def add_designer_to_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
    team_id: int = Path(..., description="Team ID"),
    designer_id: int = Query(..., description="Designer ID"),
):
    return await db_repo.admin_designer_team.add_designer_to_team(team_id=team_id, designer_id=designer_id)


@admin_designers_team_router.delete("/{team_id}/remove_designer", response_model=MessageSchema)
async def remove_designer_from_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
    team_id: int = Path(..., description="Team ID"),
    designer_id: int = Query(..., description="Designer ID"),
):
    return await db_repo.admin_designer_team.remove_designer_from_team(team_id=team_id, designer_id=designer_id)


@admin_designers_team_router.post("/add_lead", response_model=DesignerTeamDetailsSchema)
async def add_lead_to_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    data: AddLeadDesignerTeamSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_designer_team.add_lead_designer_to_team(team_id=data.team_id, lead_id=data.lead_id)


@admin_designers_team_router.delete("/remove_lead", response_model=MessageSchema)
async def remove_lead_from_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int,
    lead_id: int,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_designer_team.remove_lead_designer_from_team(team_id=team_id, lead_id=lead_id)
