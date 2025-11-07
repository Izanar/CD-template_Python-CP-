import structlog
from fastapi import HTTPException
from sqlalchemy import delete, insert, select, update
from starlette import status

from app.models import MediaBuyersTeam, MediaBuyersTeamMembers
from app.repository.admin.teams.media_buyer_team.base import AdminMediaBuyerTeamBaseRepository
from app.repository.admin.teams.media_buyer_team.utils import (
    check_media_buyer_in_team,
    check_team_by_id,
    check_team_name_exists,
    check_team_prefix,
    ensure_media_buyer_not_in_team,
    ensure_team_has_lead,
    get_designer_user,
    get_media_buyer,
    get_media_buyer_user,
    get_team,
    is_responsible_designer_in_team,
)
from app.repository.designers.lead_designer.utils import get_user
from app.repository.engine.database import DatabaseEngineRepository
from app.schemas.enums.user import UserRole
from app.schemas.media_buyer_team import CreateMediaBuyerTeamSchema, UpdateMediaBuyerTeamSchema
from app.schemas.message import MessageSchema

logger = structlog.get_logger()


class AdminMediaBuyerTeamRepository(AdminMediaBuyerTeamBaseRepository, DatabaseEngineRepository):
    async def create_team(
        self,
        team_info: CreateMediaBuyerTeamSchema,
    ) -> MediaBuyersTeam:
        async with self.session_maker() as db:
            await check_team_name_exists(db=db, team_name=team_info.name)
            await check_team_prefix(db=db, prefix=team_info.prefix)

            team = MediaBuyersTeam(**team_info.model_dump())

            db.add(team)
            await db.commit()

            return await get_team(team_id=team.id, db_session_maker=db)

    async def update_team(
        self,
        team_id: int,
        data: UpdateMediaBuyerTeamSchema,
    ) -> MediaBuyersTeam:
        async with self.session_maker() as db:
            existing_team = await check_team_by_id(
                db=db,
                team_id=team_id,
            )
            if data.name and data.name != existing_team.name:
                await check_team_name_exists(
                    db=db,
                    team_name=data.name,
                    team_id=team_id,
                )
            if data.prefix and data.prefix != existing_team.prefix:
                await check_team_prefix(db=db, prefix=data.prefix)

            stmt = (
                update(MediaBuyersTeam)
                .where(MediaBuyersTeam.id == team_id)
                .values(**data.model_dump(exclude_none=True))
                .returning(MediaBuyersTeam)
            )

            result = await db.execute(stmt)

            await db.commit()

            team = result.scalar()
            return await get_team(team_id=team.id, db_session_maker=db)

    async def delete_team(self, team_id: int) -> MessageSchema:
        async with self.session_maker() as db:
            team = await check_team_by_id(db=db, team_id=team_id)

            team.is_deleted = True
            team.lead_id = None
            team.responsible_designer = None
            team.responsible_web_master = None

            await db.execute(delete(MediaBuyersTeamMembers).where(MediaBuyersTeamMembers.team_id == team_id))

            await db.commit()
            return MessageSchema(message=f"Team with id {team_id} was deleted successfully")

    async def add_buyer_to_team(
        self,
        team_id: int,
        buyer_id: int,
    ) -> MediaBuyersTeam:
        async with self.session_maker() as db:
            team = await get_team(db_session_maker=db, team_id=team_id)

            await ensure_team_has_lead(team=team)

            await get_media_buyer_user(db_session_maker=db, buyer_id=buyer_id)

            await ensure_media_buyer_not_in_team(db_session_maker=db, team_id=team_id, buyer_id=buyer_id)

            stmt = insert(MediaBuyersTeamMembers).values(
                media_buyer_id=buyer_id,
                team_id=team_id,
            )
            await db.execute(stmt)
            await db.commit()
            await db.refresh(team)
            return team

    async def remove_buyer_from_team(
        self,
        team_id: int,
        buyer_id: int,
    ) -> MessageSchema:
        async with self.session_maker() as db:
            await get_team(db_session_maker=db, team_id=team_id)

            await get_media_buyer(db_session_maker=db, buyer_id=buyer_id)

            await check_media_buyer_in_team(db_session_maker=db, team_id=team_id, buyer_id=buyer_id)

            stmt = delete(MediaBuyersTeamMembers).filter_by(media_buyer_id=buyer_id, team_id=team_id)

            await db.execute(stmt)
            await db.commit()

            return MessageSchema(message=f"Media Buyer {buyer_id} was removed from team {team_id} successfully")

    async def add_lead_media_buyer_to_team(self, lead_id: int, team_id: int):
        async with self.session_maker() as db:
            team = await get_team(db_session_maker=db, team_id=team_id)

            stmt_check = select(MediaBuyersTeam).where(
                MediaBuyersTeam.lead_id == lead_id, MediaBuyersTeam.id != team_id
            )

            if await db.scalar(stmt_check):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already a lead in another team. Remove them from that team first.",
                )

            user = await get_user(db=db, user_id=lead_id)

            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            if user.role != UserRole.lead_media_buyer:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User must have role 'lead_media_buyer' to be assigned as team lead",
                )

            stmt = (
                update(MediaBuyersTeam)
                .where(MediaBuyersTeam.id == team_id)
                .values(lead_id=lead_id)
                .returning(MediaBuyersTeam)
            )
            await db.execute(stmt)
            await db.commit()

            await self.add_buyer_to_team(team_id=team_id, buyer_id=lead_id)
            await db.refresh(team)
            return team

    async def add_responsible_designer(
        self,
        team_id: int,
        responsible_designer_id: int,
    ) -> MediaBuyersTeam:
        async with self.session_maker() as db:
            team = await get_team(db_session_maker=db, team_id=team_id)

            await get_designer_user(db, designer_id=responsible_designer_id)

            stmt = (
                update(MediaBuyersTeam)
                .where(MediaBuyersTeam.id == team_id)
                .values(responsible_designer=responsible_designer_id)
                .returning(MediaBuyersTeam)
            )

            await db.scalar(stmt)

            await db.commit()
            await db.refresh(team)
            return team

    async def remove_responsible_designer(
        self,
        team_id: int,
        responsible_designer_id: int,
    ) -> MessageSchema:
        async with self.session_maker() as db:
            await get_team(db_session_maker=db, team_id=team_id)

            await get_designer_user(
                db=db,
                designer_id=responsible_designer_id,
            )

            await is_responsible_designer_in_team(
                db=db,
                team_id=team_id,
                designer_id=responsible_designer_id,
            )

            await db.execute(
                update(MediaBuyersTeam)
                .where(MediaBuyersTeam.id == team_id, MediaBuyersTeam.responsible_designer == responsible_designer_id)
                .values(responsible_designer=None)
            )

            await db.commit()

            return MessageSchema(
                message=f"Responsible designer {responsible_designer_id} was removed from team {team_id} successfully"
            )

    async def add_responsible_web_master(self, responsible_web_master_id: int, team_id: int) -> MediaBuyersTeam:
        async with self.session_maker() as db:
            await get_team(db_session_maker=db, team_id=team_id)

            stmt = (
                update(MediaBuyersTeam)
                .where(MediaBuyersTeam.id == team_id)
                .values(responsible_web_master=responsible_web_master_id)
                .returning(MediaBuyersTeam)
            )

            await db.scalar(stmt)

            await db.commit()

            return await get_team(db_session_maker=db, team_id=team_id)

    async def remove_responsible_web_master(self, team_id: int) -> MessageSchema:
        async with self.session_maker() as db:
            await get_team(db_session_maker=db, team_id=team_id)

            await db.execute(
                update(MediaBuyersTeam).where(MediaBuyersTeam.id == team_id).values(responsible_web_master=None)
            )

            await db.commit()

            return MessageSchema(message=f"Responsible web_master was removed from team {team_id} successfully")

    async def remove_lead_buyer_from_team(
        self,
        team_id: int,
        lead_id: int,
    ) -> MessageSchema:
        async with self.session_maker() as db:
            await get_team(db_session_maker=db, team_id=team_id)

            await get_media_buyer(db_session_maker=db, buyer_id=lead_id)

            await check_media_buyer_in_team(db_session_maker=db, team_id=team_id, buyer_id=lead_id)

            delete_stmt = delete(MediaBuyersTeamMembers).filter_by(media_buyer_id=lead_id, team_id=team_id)
            await db.execute(delete_stmt)

            update_stmt = update(MediaBuyersTeam).where(MediaBuyersTeam.id == team_id).values(lead_id=None)
            await db.execute(update_stmt)

            await db.commit()

            return MessageSchema(message=f"Media Buyer Lead {lead_id} was removed from team {team_id} successfully")
