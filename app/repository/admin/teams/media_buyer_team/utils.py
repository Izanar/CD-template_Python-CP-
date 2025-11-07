import structlog
from fastapi import HTTPException
from sqlalchemy import not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Designer, MediaBuyer, MediaBuyersTeam, MediaBuyersTeamMembers, User, WebMaster
from app.schemas.enums.user import UserRole

logger = structlog.get_logger(__name__)


async def check_team_name_exists(
    db, team_name: str | None = None, team_id: int | None = None
) -> MediaBuyersTeam | None:
    if team_name is None:
        return None
    query = select(MediaBuyersTeam).where(MediaBuyersTeam.name == team_name, not_(MediaBuyersTeam.is_deleted))

    if team_id is not None:
        query = query.where(MediaBuyersTeam.id != team_id)
    team = await db.scalar(query)
    if team:
        raise HTTPException(status_code=409, detail="Team with this name already exists")
    return


async def check_team_prefix(db: AsyncSession, prefix: str | None = None):
    if prefix and await db.scalar(
        select(MediaBuyersTeam).where(MediaBuyersTeam.prefix == prefix, not_(MediaBuyersTeam.is_deleted))
    ):
        raise HTTPException(status_code=409, detail="Team with this prefix already exists")


async def check_team_by_id(db, team_id: int) -> MediaBuyersTeam:
    team = await db.scalar(select(MediaBuyersTeam).where(MediaBuyersTeam.id == team_id))
    if not team or team.is_deleted:
        raise HTTPException(status_code=404, detail=f"Team with id {team_id} not found")
    return team


async def get_team(
    db_session_maker,
    team_id: int,
) -> MediaBuyersTeam:
    stmt = (
        select(MediaBuyersTeam)
        .where(MediaBuyersTeam.id == team_id)
        .options(
            selectinload(MediaBuyersTeam.responsible_designer_info).selectinload(Designer.user),
            selectinload(MediaBuyersTeam.responsible_web_master_info).selectinload(WebMaster.user),
            selectinload(MediaBuyersTeam.lead).selectinload(MediaBuyer.user),
            selectinload(MediaBuyersTeam.members).selectinload(MediaBuyer.user),
        )
    )

    team = await db_session_maker.scalar(stmt)
    if not team or team.is_deleted:
        raise HTTPException(status_code=404, detail=f"Team with id {team_id} not found")
    return team


async def get_media_buyer_user(db_session_maker, buyer_id: int) -> User | None:
    user = await db_session_maker.scalar(select(User).where(User.id == buyer_id))

    if not user:
        raise HTTPException(status_code=404, detail=f"User {buyer_id} not found")

    if user.role not in (UserRole.media_buyer, UserRole.lead_media_buyer):
        raise HTTPException(status_code=400, detail=f"User {buyer_id} is not a media buyer")


async def get_media_buyer(db_session_maker, buyer_id: int) -> MediaBuyer:
    if not await db_session_maker.scalar(select(MediaBuyer).where(MediaBuyer.id == buyer_id)):
        raise HTTPException(status_code=404, detail=f"Media Buyer {buyer_id} not found")


async def ensure_team_has_lead(team: MediaBuyersTeam) -> None:
    if not team.lead_id:
        raise HTTPException(
            status_code=403, detail="The user cannot be added to the team because the team has no Lead."
        )


async def ensure_media_buyer_not_in_team(
    db_session_maker,
    team_id: int,
    buyer_id: int,
) -> MediaBuyersTeam:
    if await db_session_maker.scalar(
        select(MediaBuyersTeamMembers).filter_by(media_buyer_id=buyer_id, team_id=team_id)
    ):
        raise HTTPException(status_code=409, detail=f"Media Buyer {buyer_id} already in team {team_id}")


async def check_media_buyer_in_team(
    db_session_maker,
    team_id: int,
    buyer_id: int,
) -> MediaBuyersTeamMembers | None:
    if not await db_session_maker.scalar(
        select(MediaBuyersTeamMembers).filter_by(media_buyer_id=buyer_id, team_id=team_id)
    ):
        raise HTTPException(status_code=404, detail=f"Media Buyer {buyer_id} not in team {team_id}")


async def get_designer_user(db, designer_id: int) -> User | None:
    user = await db.scalar(select(User).where(User.id == designer_id))

    if not user:
        raise HTTPException(status_code=404, detail=f"User {designer_id} not found")

    if user.role not in (UserRole.designer, UserRole.lead_designer):
        raise HTTPException(status_code=400, detail=f"User {designer_id} is not a designer")


async def is_responsible_designer_in_team(
    db,
    team_id: int,
    designer_id: int,
) -> MediaBuyersTeam:
    stmt = select(MediaBuyersTeam).where(
        MediaBuyersTeam.responsible_designer == designer_id,
        MediaBuyersTeam.id == team_id,
    )

    if not await db.scalar(stmt):
        raise HTTPException(status_code=404, detail=f"Responsible Designer with id {designer_id} not in team {team_id}")
