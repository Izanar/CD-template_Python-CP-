import structlog
from fastapi import HTTPException
from sqlalchemy import delete, exists, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import DesignersTeam, DesignersTeamLeads, DesignersTeamMembers
from app.repository.admin.teams.designer_team.base import AdminDesignerTeamBaseRepository
from app.repository.admin.teams.designer_team.utils import (
    check_designer_in_team,
    check_team_by_id,
    check_team_name_exists,
    ensure_designer_not_in_other_team,
    ensure_designer_not_in_team,
    ensure_designer_not_lead,
    get_designer_user,
    get_team,
)
from app.repository.designers.lead_designer.utils import get_user
from app.repository.engine.database import DatabaseEngineRepository
from app.schemas.enums.user import UserRole
from app.schemas.message import MessageSchema

logger = structlog.get_logger(__name__)


class AdminDesignerTeamRepository(AdminDesignerTeamBaseRepository, DatabaseEngineRepository):
    async def create_team(self, team_name: str) -> DesignersTeam:
        async with self.session_maker() as db:
            await check_team_name_exists(db=db, team_name=team_name)  # Raise 400 if team name already exists

            team = DesignersTeam(name=team_name)

            db.add(team)
            await db.commit()

            return await get_team(db_session_maker=db, team_id=team.id)

    async def update_team(self, team_id: int, team_name: str | None = None):
        async with self.session_maker() as db:
            await check_team_by_id(db=db, team_id=team_id)  # Raise 404 if team not found

            await check_team_name_exists(db=db, team_name=team_name)

            stmt = (
                update(DesignersTeam).where(DesignersTeam.id == team_id).values(name=team_name).returning(DesignersTeam)
            )

            await db.execute(stmt)
            await db.commit()
            return await get_team(db_session_maker=db, team_id=team_id)

    async def delete_team(self, team_id: int):
        async with self.session_maker() as db:
            team = await check_team_by_id(db=db, team_id=team_id)
            await db.delete(team)
            await db.commit()

        return MessageSchema(message=f"Team with id {team_id} was deleted successfully")

    async def add_designer_to_team(
        self,
        team_id: int,
        designer_id: int,
    ) -> DesignersTeam:
        async with self.session_maker() as db:
            team = await get_team(db_session_maker=db, team_id=team_id)  # Raise 404 if team not found

            await get_designer_user(
                db_session_maker=db,
                designer_id=designer_id,
            )

            await ensure_designer_not_in_team(
                db=db,
                team_id=team_id,
                designer_id=designer_id,
            )

            await ensure_designer_not_in_other_team(
                db=db,
                team_id=team_id,
                designer_id=designer_id,
            )

            stmt = insert(DesignersTeamMembers).values(
                designer_id=designer_id,
                team_id=team_id,
            )
            await db.execute(stmt)
            await db.commit()

            await db.refresh(team)

            return team

    async def remove_designer_from_team(
        self,
        team_id: int,
        designer_id: int,
    ) -> MessageSchema:
        async with self.session_maker() as db:
            await get_team(db_session_maker=db, team_id=team_id)  # Raise 404 if team not found

            await get_designer_user(
                db_session_maker=db,
                designer_id=designer_id,
            )

            await check_designer_in_team(
                db_session_maker=db,
                team_id=team_id,
                designer_id=designer_id,
            )  # Raise 404 if designer not in team
            await ensure_designer_not_lead(db, team_id, designer_id)

            await ensure_designer_not_in_other_team(
                db=db,
                team_id=team_id,
                designer_id=designer_id,
            )

            stmt = delete(DesignersTeamMembers).filter_by(designer_id=designer_id, team_id=team_id)
            await db.execute(stmt)
            await db.commit()

            return MessageSchema(message=f"Designer with id {designer_id} was removed from team {team_id} successfully")

    async def add_lead_designer_to_team(self, lead_id: list[int], team_id: int):
        async with self.session_maker() as db:
            await get_team(db, team_id)

            for lid in lead_id:
                user = await get_user(db, user_id=lid)
                if not user or user.role != UserRole.lead_designer:
                    raise HTTPException(
                        status_code=400,
                        detail=f"User {lid} must have role 'lead_designer'",
                    )

                already_lead = await db.scalar(
                    select(
                        exists().where(
                            DesignersTeamLeads.team_id == team_id,
                            DesignersTeamLeads.designer_id == lid,
                        )
                    )
                )
                if already_lead:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Designer {lid} is already a lead of team {team_id}",
                    )

                await ensure_designer_not_in_other_team(db, team_id, lid)

            await db.execute(
                pg_insert(DesignersTeamLeads)
                .values([{"team_id": team_id, "designer_id": lid} for lid in lead_id])
                .on_conflict_do_nothing()
            )

            await db.execute(
                pg_insert(DesignersTeamMembers)
                .values([{"team_id": team_id, "designer_id": lid} for lid in lead_id])
                .on_conflict_do_nothing()
            )

            await db.commit()
            return await get_team(db, team_id=team_id)

    async def remove_lead_designer_from_team(
        self,
        team_id: int,
        lead_id: int,
    ) -> MessageSchema:
        async with self.session_maker() as db:
            await get_team(db, team_id)

            exists_q = select(DesignersTeamLeads).where(
                DesignersTeamLeads.team_id == team_id,
                DesignersTeamLeads.designer_id == lead_id,
            )
            if not (await db.scalar(exists_q)):
                raise HTTPException(status_code=404, detail="Designer is not a lead of this team")

            await db.execute(
                delete(DesignersTeamLeads).where(
                    DesignersTeamLeads.team_id == team_id,
                    DesignersTeamLeads.designer_id == lead_id,
                )
            )
            await db.execute(
                delete(DesignersTeamMembers).where(
                    DesignersTeamMembers.team_id == team_id,
                    DesignersTeamMembers.designer_id == lead_id,
                )
            )
            await db.commit()

            return MessageSchema(message=f"Designer {lead_id} is no longer a lead of team {team_id}")
