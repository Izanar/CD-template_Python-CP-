from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import WebMastersTeam
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.web_masters.web_master_team.base import WebMasterTeamBaseRepository


class WebMasterTeamRepository(WebMasterTeamBaseRepository, DatabaseEngineRepository):
    async def get_team_by_id(self, team_id: int):
        async with self.session_maker() as db:
            if team := await db.scalar(select(WebMastersTeam).where(WebMastersTeam.id == team_id)):
                return team

            raise HTTPException(status_code=404, detail=f"Team with id {team_id} not found")

    async def get_all_web_master_teams(self, limit: int, offset: int):
        async with self.session_maker() as db:
            stmt = select(WebMastersTeam).options(selectinload(WebMastersTeam.members))

            stmt = stmt.limit(limit).offset(offset)

            result = await db.execute(stmt)
            return result.scalars().all()

    async def get_total_teams(self):
        async with self.session_maker() as db:
            return await db.scalar(select(func.count()).select_from(WebMastersTeam))

    async def get_team_details(self, team_id: int):
        async with self.session_maker() as db:
            await self.get_team_by_id(team_id)

            return await db.scalar(
                select(WebMastersTeam).options(selectinload(WebMastersTeam.members)).where(WebMastersTeam.id == team_id)
            )
