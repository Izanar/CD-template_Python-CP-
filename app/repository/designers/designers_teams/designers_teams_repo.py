from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import Designer, DesignersTeam
from app.repository.designers.designers_teams.base import DesignerTeamBaseRepository
from app.repository.designers.designers_teams.utils import get_team_by_id
from app.repository.engine.database import DatabaseEngineRepository


class DesignersTeamsRepository(DesignerTeamBaseRepository, DatabaseEngineRepository):
    async def get_total_teams(self):
        async with self.session_maker() as db:
            return await db.scalar(select(func.count()).select_from(DesignersTeam))

    async def get_all_designers_teams(self, limit: int, offset: int):
        async with self.session_maker() as db:
            stmt = (
                select(DesignersTeam)
                .options(
                    selectinload(DesignersTeam.leads).joinedload(Designer.user),
                    selectinload(DesignersTeam.members).joinedload(Designer.user),
                )
                .order_by(func.lower(DesignersTeam.name))
                .limit(limit)
                .offset(offset)
            )

            result = await db.execute(stmt)
            return result.scalars().all()

    async def get_team_details(self, team_id: int):
        async with self.session_maker() as db:
            await get_team_by_id(db, team_id)

            return await db.scalar(
                select(DesignersTeam)
                .options(
                    selectinload(DesignersTeam.leads).joinedload(Designer.user),
                    selectinload(DesignersTeam.members).joinedload(Designer.user),
                )
                .where(DesignersTeam.id == team_id)
            )
