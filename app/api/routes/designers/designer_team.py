from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependecies.auth import AuthenticateDesignerOrLead, AuthenticateLeadDesigner
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import DesignersTeam, User
from app.repository.database.base import DatabaseRepository
from app.schemas.designers.designer_team_schema import (
    DesignerTeamDetailsSchema,
)
from app.schemas.pagination import PaginationResponse

designer_team_router = APIRouter(
    prefix="/lead_designer/team",
    tags=["Lead Designer"],
)


@designer_team_router.get("/all", response_model=PaginationResponse[DesignerTeamDetailsSchema])
async def view_designer_teams(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    current_user: User = Depends(AuthenticateDesignerOrLead()),
    limit: int = Query(10, ge=1, le=100, description="Limit of tasks per page"),
    offset: int = Query(0, ge=0, description="Offset of teams"),
):
    teams = await db_repo.designers_teams.get_all_designers_teams(
        limit=limit,
        offset=offset,
    )

    tasks_schema = [DesignerTeamDetailsSchema.model_validate(team) for team in teams]

    total = await db_repo.designers_teams.get_total_teams()

    return PaginationResponse.create(items=tasks_schema, total=total, limit=limit, offset=offset)


@designer_team_router.get("/{team_id}", response_model=DesignerTeamDetailsSchema)
async def view_designer_team_details(
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    team_id: int,
    current_user: User = Depends(AuthenticateLeadDesigner()),
) -> DesignersTeam:
    return await db_repo.designers_teams.get_team_details(team_id=team_id)
