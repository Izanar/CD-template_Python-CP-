from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from ..factories.http_client_factory import KeitaroHttpClientFactory
from ..utils import (
    filter_regular_streams,
    get_effective_creo,
    handle_keitaro_404_error,
    update_adname_in_utm_filter,
    validate_campaign_stream_match,
    validate_stream_creative_association,
)


class StreamService:
    def __init__(self, campaign_service=None, creative_service=None):
        self.campaign_service = campaign_service
        self.creative_service = creative_service

    async def get_campaign_streams(self, campaign_id: int, keitaro_config: Dict[str, str]) -> List[Dict[str, Any]]:
        http_client = KeitaroHttpClientFactory.create(keitaro_config)
        streams = await self._fetch_campaign_streams(campaign_id, http_client)
        return filter_regular_streams(streams)

    async def _fetch_campaign_streams(self, campaign_id: int, http_client) -> List[Dict[str, Any]]:
        try:
            return await http_client.get(f"/campaigns/{campaign_id}/streams")
        except HTTPException as e:
            handle_keitaro_404_error(e, "Campaign", campaign_id)

    async def get_stream(self, stream_id: int, keitaro_config: Dict[str, str]) -> Dict[str, Any]:
        http_client = KeitaroHttpClientFactory.create(keitaro_config)
        try:
            return await http_client.get(f"/streams/{stream_id}")
        except HTTPException as e:
            handle_keitaro_404_error(e, "Stream", stream_id)

    async def update_stream(
        self, stream_id: int, stream_data: Dict[str, Any], keitaro_config: Dict[str, str]
    ) -> Dict[str, Any]:
        http_client = KeitaroHttpClientFactory.create(keitaro_config)
        try:
            return await http_client.put(f"/streams/{stream_id}", data=stream_data)
        except HTTPException as e:
            handle_keitaro_404_error(e, "Stream", stream_id)

    async def add_adname_to_stream(
        self,
        campaign_id: int,
        stream_id: int,
        creative_id: int,
        db_repo,
        keitaro_config: Dict[str, str],
        user_id_to_save: Optional[int] = None,
    ) -> Dict[str, Any]:
        creative = await self.creative_service.validate_creative_exists(creative_id, db_repo)

        stream_data = await self.get_stream(stream_id, keitaro_config)

        validate_campaign_stream_match(stream_data.get("campaign_id"), campaign_id, stream_id)

        user_creo = creative.task.created_by.creo if creative.task.created_by else None
        effective_creo = get_effective_creo(user_creo, keitaro_config["creo"])
        update_adname_in_utm_filter(stream_data, creative.ad_name, effective_creo, "add")
        await self.update_stream(stream_id, stream_data, keitaro_config)
        stream_name = stream_data.get("name", f"Stream {stream_id}")

        campaign_data = await self.campaign_service.get_campaign_by_id(campaign_id, keitaro_config)
        campaign_name = campaign_data.get("name", f"Campaign {campaign_id}")

        await self.creative_service.save_campaign_stream_info_to_creative(
            campaign_id, campaign_name, stream_id, stream_name, creative_id, db_repo, user_id_to_save
        )

        return await self.creative_service.get_creative_response(creative_id, db_repo)

    async def remove_adname_from_stream(
        self, stream_id: int, creative_id: int, db_repo, keitaro_config: Dict[str, str]
    ) -> Dict[str, Any]:
        creative = await self.creative_service.validate_creative_exists(creative_id, db_repo)

        validate_stream_creative_association(creative, stream_id, creative_id)

        if not creative.campaign_id:
            raise HTTPException(status_code=400, detail="Creative does not have associated campaign")

        campaign_id = creative.campaign_id

        stream_data = await self.get_stream(stream_id, keitaro_config)
        validate_campaign_stream_match(stream_data.get("campaign_id"), campaign_id, stream_id)

        user_creo = creative.task.created_by.creo if creative.task.created_by else None
        effective_creo = get_effective_creo(user_creo, keitaro_config["creo"])

        update_adname_in_utm_filter(stream_data, creative.ad_name, effective_creo, "remove")
        await self.update_stream(stream_id, stream_data, keitaro_config)
        stream_name = stream_data.get("name", f"Stream {stream_id}")

        campaign_data = await self.campaign_service.get_campaign_by_id(campaign_id, keitaro_config)
        campaign_name = campaign_data.get("name", f"Campaign {campaign_id}")

        await self.creative_service.remove_campaign_stream_info_from_creative(
            campaign_id, campaign_name, stream_id, stream_name, creative_id, db_repo
        )

        return await self.creative_service.get_creative_response(creative_id, db_repo)
