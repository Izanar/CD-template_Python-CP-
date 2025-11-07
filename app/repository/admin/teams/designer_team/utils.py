from fastapi import HTTPException
from sqlalchemy import exists, select
from sqlalchemy.orm import joinedload

from app.models import Designer, DesignersTeam, DesignersTeamLeads, DesignersTeamMembers, User
from app.schemas.enums.user import UserRole


async def check_team_name_exists(db, team_name: str):
    team = await db.scalar(select(DesignersTeam).where(DesignersTeam.name == team_name))

    if team:
        raise HTTPException(status_code=409, detail="Team with this name already exists")


async def check_team_by_id(db, team_id: int):
    if team := await db.scalar(select(DesignersTeam).where(DesignersTeam.id == team_id)):
        return team

    raise HTTPException(status_code=404, detail=f"Team with id {team_id} not found")


async def get_team(
    db_session_maker,
    team_id: int,
) -> DesignersTeam:
    stmt = (
        select(DesignersTeam)
        .options(
            joinedload(DesignersTeam.leads).joinedload(Designer.user),
            joinedload(DesignersTeam.members).joinedload(Designer.user),
        )
        .where(DesignersTeam.id == team_id)
    )

    if team := await db_session_maker.scalar(stmt):
        return team

    raise HTTPException(status_code=404, detail=f"Team {team_id} not found")


async def get_designer_user(db_session_maker, designer_id: int) -> User | None:
    user = await db_session_maker.scalar(select(User).where(User.id == designer_id))

    if not user:
        raise HTTPException(status_code=404, detail=f"User {designer_id} not found")

    if user.role not in (UserRole.designer, UserRole.lead_designer):
        raise HTTPException(status_code=400, detail=f"User {designer_id} is not a designer")


async def check_designer_in_team(
    db_session_maker,
    team_id: int,
    designer_id: int,
) -> DesignersTeam:
    stmt = select(DesignersTeamMembers).where(
        DesignersTeamMembers.designer_id == designer_id,
        DesignersTeamMembers.team_id == team_id,
    )

    if not await db_session_maker.scalar(stmt):
        raise HTTPException(status_code=404, detail=f"Designer {designer_id} not in team {team_id}")


async def ensure_team_has_lead(team: DesignersTeam) -> None:
    if not team.lead_id:
        raise HTTPException(
            status_code=403, detail="The user cannot be added to the team because the team has no Lead."
        )


async def ensure_designer_not_in_team(
    db,
    team_id: int,
    designer_id: int,
) -> None:
    stmt = select(DesignersTeamMembers).where(
        DesignersTeamMembers.designer_id == designer_id, DesignersTeamMembers.team_id == team_id
    )

    if await db.scalar(stmt):
        raise HTTPException(status_code=400, detail=f"Designer {designer_id} already in team {team_id}")


async def ensure_designer_not_in_other_team(
    db,
    team_id: int,
    designer_id: int,
):
    stmt = select(DesignersTeamMembers).where(
        DesignersTeamMembers.designer_id == designer_id,
        DesignersTeamMembers.team_id != team_id,
    )

    if await db.scalar(stmt):
        raise HTTPException(status_code=400, detail=f"Designer {designer_id} already in another team")


async def ensure_designer_not_lead(db, team_id: int, designer_id: int) -> None:
    is_lead = await db.scalar(
        select(
            exists().where(
                DesignersTeamLeads.team_id == team_id,
                DesignersTeamLeads.designer_id == designer_id,
            )
        )
    )
    if is_lead:
        raise HTTPException(
            status_code=400,
            detail=(f"Designer {designer_id} is a lead of team {team_id}. Remove lead role first."),
        )
