from typing import Dict

from fastapi import HTTPException
from sqlalchemy import select

from app.models import KeitaroConfig, MediaBuyersTeam, MediaBuyersTeamMembers, User
from app.repository.engine.database import DatabaseEngineRepository
from app.repository.keitaro.base import KeitaroBaseRepository
from app.repository.media_buyers.assistant.utils import get_keitaro_config_user_id, get_keitaro_username_for_media_buyer


class KeitaroRepository(KeitaroBaseRepository, DatabaseEngineRepository):
    async def get_user_keitaro_config(self, current_user: User) -> Dict[str, str]:
        async with self.session_maker() as db:
            config_user_id = await get_keitaro_config_user_id(db, current_user)

            query = (
                select(KeitaroConfig)
                .join(MediaBuyersTeam, KeitaroConfig.id == MediaBuyersTeam.keitaro_config_id)
                .join(MediaBuyersTeamMembers, MediaBuyersTeam.id == MediaBuyersTeamMembers.team_id)
                .where(MediaBuyersTeamMembers.media_buyer_id == config_user_id)
            )
            config = await db.execute(query)
            result = config.scalar_one_or_none()

            if not result or not result.base_url or not result.api_key:
                raise HTTPException(status_code=400, detail="User does not have Keitaro configuration.")

            username_to_use = await get_keitaro_username_for_media_buyer(db, current_user)

            return {
                "base_url": result.base_url,
                "api_key": result.api_key,
                "name": result.name,
                "creo": result.creo,
                "username": username_to_use,
            }
