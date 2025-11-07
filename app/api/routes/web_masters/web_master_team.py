from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query

from app.dependecies.auth import AuthenticateLeadWebMaster
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.pagination import PaginationResponse
from app.schemas.web_masters.web_master_team import (
    WebMasterTeamDetailsSchema,
)

web_master_team_router = APIRouter(
    prefix="/lead_web_master/team",
    tags=["Lead Web Master"],
)


logger = structlog.get_logger(__name__)


@web_master_team_router.get("/all", response_model=PaginationResponse[WebMasterTeamDetailsSchema])
async def view_web_masters_teams(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateLeadWebMaster()),
    limit: int = Query(10, ge=1, le=100, description="Limit of tasks per page"),
    offset: int = Query(0, ge=0, description="Offset of teams"),
):
    teams = await db_repo.web_masters_teams.get_all_web_master_teams(
        limit=limit,
        offset=offset,
    )

    tasks_schema = [WebMasterTeamDetailsSchema.model_validate(team) for team in teams]

    total = await db_repo.web_masters_teams.get_total_teams()

    return PaginationResponse.create(items=tasks_schema, total=total, limit=limit, offset=offset)


@web_master_team_router.get("/{team_id}", response_model=WebMasterTeamDetailsSchema)
async def view_web_master_team_details(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int,
    current_user: User = Depends(AuthenticateLeadWebMaster()),
):
    return await db_repo.web_masters_teams.get_team_details(team_id=team_id)
