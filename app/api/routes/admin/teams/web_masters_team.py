from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query

from app.dependecies.auth import AuthenticateAdmin
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.message import MessageSchema
from app.schemas.web_masters.web_master_team import (
    AddLeadWebMasterTeamSchema,
    CreateWebMasterTeamSchema,
    UpdateWebMasterTeamSchema,
    WebMasterTeamDetailsSchema,
    WebMasterTeamSchema,
)

admin_web_masters_team_router = APIRouter(
    prefix="/admin/web_master_team",
    tags=["Admin"],
)


@admin_web_masters_team_router.post("/create", response_model=WebMasterTeamSchema)
async def create_web_master_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team: CreateWebMasterTeamSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_web_master_team.create_team(team_name=team.team_name)


@admin_web_masters_team_router.patch("/{team_id}/update", response_model=UpdateWebMasterTeamSchema)
async def update_web_master_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
    team_id: int = Path(..., description="Web Master team ID"),
    update_data: UpdateWebMasterTeamSchema = Body(..., description="Update data"),
):
    return await db_repo.admin_web_master_team.update_team(team_id=team_id, update_data=update_data)


@admin_web_masters_team_router.delete("/{team_id}/remove", response_model=MessageSchema)
async def remove_web_masters_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
    team_id: int = Path(..., description="Team ID"),
):
    return await db_repo.admin_web_master_team.remove_team(team_id=team_id)


@admin_web_masters_team_router.post("/{team_id}/add_web_master", response_model=WebMasterTeamDetailsSchema)
async def add_web_master_to_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
    team_id: int = Path(..., description="Team ID"),
    web_master_id: int = Query(..., description="Web Master ID"),
):
    return await db_repo.admin_web_master_team.add_web_master_to_team(
        user=current_user, team_id=team_id, web_master_id=web_master_id
    )


@admin_web_masters_team_router.delete("/{team_id}/remove_web_master", response_model=MessageSchema)
async def remove_web_master_from_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateAdmin()),
    team_id: int = Path(..., description="Team ID"),
    web_master_id: int = Query(..., description="Web Master ID"),
):
    return await db_repo.admin_web_master_team.remove_web_master_from_team(
        user=current_user, team_id=team_id, web_master_id=web_master_id
    )


@admin_web_masters_team_router.post("/add_lead", response_model=WebMasterTeamSchema)
async def add_lead_to_team(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    data: AddLeadWebMasterTeamSchema,
    current_user: User = Depends(AuthenticateAdmin()),
):
    return await db_repo.admin_web_master_team.add_lead_web_master_to_team(team_id=data.team_id, lead_id=data.lead_id)
