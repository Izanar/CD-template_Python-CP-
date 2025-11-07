from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import User, WebMaster, WebMastersTeam, WebMastersTeamMembers
from app.schemas.enums.user import UserRole


async def check_team_name_exists(db, team_name: str):
    team = await db.scalar(select(WebMastersTeam).where(WebMastersTeam.name == team_name))

    if team:
        raise HTTPException(status_code=409, detail="Team with this name already exists")


async def check_team_by_id(db, team_id: int):
    if team := await db.scalar(select(WebMastersTeam).where(WebMastersTeam.id == team_id)):
        return team

    raise HTTPException(status_code=404, detail=f"Team with id {team_id} not found")


async def get_team(
    db_session_maker,
    team_id: int,
) -> WebMastersTeam:
    stmt = select(WebMastersTeam).options(selectinload(WebMastersTeam.members)).where(WebMastersTeam.id == team_id)

    if team := await db_session_maker.scalar(stmt):
        return team

    raise HTTPException(status_code=404, detail=f"Team {team_id} not found")


async def get_web_master_user(db_session_maker, web_master_id: int) -> User | None:
    user = await db_session_maker.scalar(select(User).where(User.id == web_master_id))

    if not user:
        raise HTTPException(status_code=404, detail=f"User {web_master_id} not found")

    if user.role != UserRole.web_master:
        raise HTTPException(status_code=400, detail=f"User {web_master_id} is not a web master")


async def check_web_master_in_team(
    db_session_maker,
    team_id: int,
    web_master_id: int,
) -> WebMastersTeamMembers | None:
    if not await db_session_maker.scalar(
        select(WebMastersTeamMembers).filter_by(web_master_id=web_master_id, team_id=team_id)
    ):
        raise HTTPException(status_code=404, detail=f"Web Master {web_master_id} not in team {team_id}")


async def ensure_web_master_not_in_team(
    db_session_maker,
    team_id: int,
    web_master_id: int,
) -> WebMastersTeamMembers | None:
    if not await db_session_maker.scalar(select(WebMaster.id).where(WebMaster.id == web_master_id)):
        raise HTTPException(status_code=404, detail=f"Web Master {web_master_id} not found")

    if await db_session_maker.scalar(
        select(WebMastersTeamMembers).filter_by(web_master_id=web_master_id, team_id=team_id)
    ):
        raise HTTPException(status_code=409, detail=f"Web Master {web_master_id} already in team {team_id}")


async def ensure_team_has_lead(team: WebMastersTeam) -> None:
    if not team.lead_id:
        raise HTTPException(
            status_code=403, detail="The user cannot be added to the team because the team has no Lead."
        )


async def get_lead_web_master_user(db_session_maker, web_master_id: int) -> User:
    user = await db_session_maker.scalar(select(User).where(User.id == web_master_id))
    if not user:
        raise HTTPException(status_code=404, detail=f"User {web_master_id} not found")
    if user.role != UserRole.lead_web_master:
        raise HTTPException(status_code=400, detail=f"User {web_master_id} is not a Lead Web Master")
    return user
