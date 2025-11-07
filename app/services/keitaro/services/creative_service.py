from typing import Any, Dict, Optional

from fastapi import HTTPException

from app.schemas.creative import CreativeUpdateSchema


class CreativeService:
    async def validate_creative_exists(self, creative_id: int, db_repo) -> Any:
        creative = await db_repo.creative.get_creative_by_id(creative_id)

        if not creative.ad_name:
            raise HTTPException(status_code=400, detail="Creative does not have adname")

        return creative

    async def save_campaign_stream_info_to_creative(
        self,
        campaign_id: int,
        campaign_name: str,
        stream_id: int,
        stream_name: str,
        creative_id: int,
        db_repo,
        user_id_to_save: Optional[int] = None,
    ) -> None:
        current_creative = await db_repo.creative.get_creative_by_id(creative_id)
        current_streams = current_creative.streams if hasattr(current_creative, "streams") else []

        if not any(stream.get("id") == stream_id for stream in current_streams):
            current_streams.append({"id": stream_id, "name": stream_name})

        update_data = CreativeUpdateSchema(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            streams_data=current_streams,
        )

        if user_id_to_save is not None:
            update_data.keitaro_config_user_id = user_id_to_save

        await db_repo.creative.update_creative_fields(creative_id, update_data)

    async def remove_campaign_stream_info_from_creative(
        self, campaign_id: int, campaign_name: str, stream_id: int, stream_name: str, creative_id: int, db_repo
    ) -> None:
        current_creative = await db_repo.creative.get_creative_by_id(creative_id)
        current_streams = current_creative.streams if hasattr(current_creative, "streams") else []

        current_streams = [stream for stream in current_streams if stream.get("id") != stream_id]

        update_data = CreativeUpdateSchema(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            streams_data=current_streams,
        )
        await db_repo.creative.update_creative_fields(creative_id, update_data)

    async def get_creative_response(self, creative_id: int, db_repo) -> Dict[str, Any]:
        from app.schemas.creative import CreativeResponseSchema

        updated_creative = await db_repo.creative.get_creative_by_id(creative_id)
        return CreativeResponseSchema.model_validate(updated_creative).model_dump()
