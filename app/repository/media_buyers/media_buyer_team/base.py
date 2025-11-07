from abc import ABC, abstractmethod
from typing import Sequence

from app.models import MediaBuyersTeam, User


class MediaBuyerTeamBaseRepository(ABC):
    @abstractmethod
    async def get_media_buyer_teams(
        self,
        user: User,
        limit: int,
        offset: int,
    ) -> Sequence[MediaBuyersTeam]:
        pass

    @abstractmethod
    async def get_media_buyer_team(
        self,
        user: User,
        team_id: int,
    ) -> MediaBuyersTeam:
        pass

    @abstractmethod
    async def get_total_teams(self) -> int:
        pass
