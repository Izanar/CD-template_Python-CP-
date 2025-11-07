from typing import Any, Dict, List

from fastapi import HTTPException

from ..factories.http_client_factory import KeitaroHttpClientFactory
from ..settings import settings
from ..utils import (
    filter_campaigns_by_group_id,
    find_user_by_username,
    handle_keitaro_404_error,
    resolve_campaign_group_id,
)


class CampaignService:
    def __init__(self):
        self.campaigns_limit = settings.campaigns_limit

    async def get_user_campaigns(self, username: str, keitaro_config: Dict[str, str]) -> List[Dict[str, Any]]:
        http_client = KeitaroHttpClientFactory.create(keitaro_config)
        user = await self._find_user_by_username(username, http_client)
        group_id = await self._resolve_campaign_group_id(user, username, http_client)

        if not group_id:
            return []

        return await self._get_campaigns_by_group_id(group_id, http_client)

    async def _find_user_by_username(self, username: str, http_client) -> Dict[str, Any]:
        users = await self._fetch_users(http_client)
        return find_user_by_username(users, username)

    async def _resolve_campaign_group_id(self, user: Dict[str, Any], username: str, http_client) -> int | None:
        groups = await self._fetch_campaign_groups(http_client)
        return resolve_campaign_group_id(user, username, groups)

    async def _get_campaigns_by_group_id(self, group_id: int, http_client) -> List[Dict[str, Any]]:
        all_campaigns = await self._fetch_all_campaigns(http_client)
        return filter_campaigns_by_group_id(all_campaigns, group_id)

    async def _fetch_users(self, http_client) -> List[Dict[str, Any]]:
        return await http_client.get("/users")

    async def _fetch_campaign_groups(self, http_client) -> List[Dict[str, Any]]:
        return await http_client.get("/groups", params={"type": "campaigns"})

    async def _fetch_all_campaigns(self, http_client) -> List[Dict[str, Any]]:
        return await http_client.get("/campaigns", params={"limit": self.campaigns_limit})

    async def get_campaign_by_id(self, campaign_id: int, keitaro_config: Dict[str, str]) -> Dict[str, Any]:
        http_client = KeitaroHttpClientFactory.create(keitaro_config)
        try:
            return await http_client.get(f"/campaigns/{campaign_id}")
        except HTTPException as e:
            handle_keitaro_404_error(e, "Campaign", campaign_id)
