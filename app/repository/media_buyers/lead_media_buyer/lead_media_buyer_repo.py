import structlog
from sqlalchemy import select

from app.models import MediaBuyersTeamMembers, User
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.media_buyers.lead_media_buyer.base import LeadMediaBuyerBaseRepository

logger = structlog.get_logger()


class LeadMediaBuyerRepository(LeadMediaBuyerBaseRepository, DatabaseEngineRepository):
    async def get_media_buyers_by_team(self, team_id: list[int]) -> list[User]:
        async with self.session_maker() as session:
            stmt = (
                select(User)
                .join(MediaBuyersTeamMembers, MediaBuyersTeamMembers.media_buyer_id == User.id)
                .where(MediaBuyersTeamMembers.team_id.in_(team_id))
            )
            result = await session.scalars(stmt)
            return result.all()
