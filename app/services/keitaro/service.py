from typing import Any, Dict, List

from .services import CampaignService, CreativeService, StreamService


class KeitaroService:
    def __init__(self, keitaro_config: Dict[str, str]):
        self.keitaro_config = keitaro_config
        self.campaign_service = CampaignService()
        self.creative_service = CreativeService()
        self.stream_service = StreamService(
            campaign_service=self.campaign_service, creative_service=self.creative_service
        )

    async def get_user_campaigns(self, username: str) -> Dict[str, Any]:
        return await self.campaign_service.get_user_campaigns(username, self.keitaro_config)

    async def get_campaign_streams(self, campaign_id: int) -> List[Dict[str, Any]]:
        return await self.stream_service.get_campaign_streams(campaign_id, self.keitaro_config)

    async def get_campaign_by_id(self, campaign_id: int) -> Dict[str, Any]:
        return await self.campaign_service.get_campaign_by_id(campaign_id, self.keitaro_config)

    async def add_adname_to_stream(
        self, campaign_id: int, stream_id: int, creative_id: int, db_repo, user_id_to_save: int | None = None
    ) -> Dict[str, Any]:
        return await self.stream_service.add_adname_to_stream(
            campaign_id, stream_id, creative_id, db_repo, self.keitaro_config, user_id_to_save
        )

    async def remove_adname_from_stream(self, stream_id: int, creative_id: int, db_repo) -> Dict[str, Any]:
        return await self.stream_service.remove_adname_from_stream(stream_id, creative_id, db_repo, self.keitaro_config)
