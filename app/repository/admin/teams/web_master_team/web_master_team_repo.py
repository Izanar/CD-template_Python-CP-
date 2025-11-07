import structlog
from sqlalchemy import delete, insert, update

from app.models import User, WebMastersTeam, WebMastersTeamMembers
from app.repository.admin.teams.web_master_team.base import AdminWebMasterTeamBaseRepository
from app.repository.admin.teams.web_master_team.utils import (
    check_team_by_id,
    check_team_name_exists,
    check_web_master_in_team,
    ensure_team_has_lead,
    ensure_web_master_not_in_team,
    get_lead_web_master_user,
    get_team,
    get_web_master_user,
)
from app.repository.engine.database import DatabaseEngineRepository
from app.schemas.message import MessageSchema
from app.schemas.web_masters.web_master_team import UpdateWebMasterTeamSchema

logger = structlog.get_logger()


class AdminWebMasterTeamRepository(AdminWebMasterTeamBaseRepository, DatabaseEngineRepository):
    async def create_team(self, team_name: str) -> WebMastersTeam:
        async with self.session_maker() as db:
            await check_team_name_exists(
                db=db,
                team_name=team_name,
            )  # 409 if team name exists

            team = WebMastersTeam(name=team_name)

            db.add(team)
            await db.commit()

            return team

    async def update_team(self, team_id: int, update_data: UpdateWebMasterTeamSchema):
        async with self.session_maker() as db:
            team = await check_team_by_id(
                db=db,
                team_id=team_id,
            )  # 404 if team not found
            if update_data.name and update_data.name != team.name:
                await check_team_name_exists(
                    db=db,
                    team_name=update_data.name,
                )  # 409 if team name exists

            stmt = (
                update(WebMastersTeam)
                .where(WebMastersTeam.id == team_id)
                .values(name=update_data.name, lead_id=update_data.lead_id)
                .returning(WebMastersTeam)
            )

            result = await db.execute(stmt)

            await db.commit()

            return result.scalar()

    async def remove_team(self, team_id: int) -> MessageSchema:
        async with self.session_maker() as db:
            team = await check_team_by_id(
                db=db,
                team_id=team_id,
            )  # 404 if team not found

            await db.delete(team)
            await db.commit()

            return MessageSchema(message=f"Team with id {team_id} was deleted successfully")

    async def add_web_master_to_team(
        self,
        user: User,
        team_id: int,
        web_master_id: int,
    ) -> WebMastersTeam:
        async with self.session_maker() as db:
            team = await get_team(db_session_maker=db, team_id=team_id)  # Raise 404 if team not found

            await ensure_team_has_lead(team=team)  # 403 if team has no lead

            await get_web_master_user(db_session_maker=db, web_master_id=web_master_id)

            await ensure_web_master_not_in_team(
                db_session_maker=db, team_id=team_id, web_master_id=web_master_id
            )  # 409 if web master already in team

            stmt = insert(WebMastersTeamMembers).values(
                web_master_id=web_master_id,
                team_id=team_id,
            )

            await db.execute(stmt)
            await db.commit()
            await db.refresh(team)
            return team

    async def remove_web_master_from_team(
        self,
        user: User,
        team_id: int,
        web_master_id: int,
    ) -> WebMastersTeam:
        async with self.session_maker() as db:
            await get_team(db_session_maker=db, team_id=team_id)  # Raise 404 if team not found

            await get_web_master_user(db_session_maker=db, web_master_id=web_master_id)  # 404 if web master not found

            await check_web_master_in_team(
                db_session_maker=db, team_id=team_id, web_master_id=web_master_id
            )  # 404 if web master not in team

            stmt = delete(WebMastersTeamMembers).filter_by(web_master_id=web_master_id, team_id=team_id)

            await db.execute(stmt)
            await db.commit()

            return MessageSchema(
                message=f"Web Master with id {web_master_id} was removed from team {team_id} successfully"
            )

    async def add_lead_web_master_to_team(self, lead_id: int, team_id: int):
        async with self.session_maker() as db:
            await get_team(db_session_maker=db, team_id=team_id)
            await get_lead_web_master_user(db_session_maker=db, web_master_id=lead_id)
            stmt = (
                update(WebMastersTeam)
                .where(
                    WebMastersTeam.id == team_id,
                )
                .values(lead_id=lead_id)
                .returning(WebMastersTeam)
            )

            result = await db.execute(stmt)

            await db.commit()

            return result.scalar()
