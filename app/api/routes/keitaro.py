from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.dependecies.auth import AuthenticateMediaBuyerOrLead
from app.dependecies.keitaro import get_keitaro_config, get_keitaro_service
from app.dependecies.stub import DatabaseRepositoryStub
from app.models import User
from app.repository.keitaro.utils import (
    get_username_for_campaigns,
    resolve_keitaro_config_user,
    resolve_user_id_for_creative,
)
from app.schemas.creative import CreativeResponseSchema
from app.schemas.keitaro import (
    KeitaroAddAdnameSchema,
    KeitaroRemoveAdnameSchema,
    KeitaroStreamsResponse,
    KeitaroUserCampaignsResponse,
)
from app.services.keitaro.service import KeitaroService

router = APIRouter(prefix="/keitaro", tags=["keitaro"])


@router.get("/user/campaigns", response_model=KeitaroUserCampaignsResponse)
async def get_user_campaigns(
    user_id: Optional[int] = Query(None, description="User ID to get campaigns for"),
    current_user: User = Depends(AuthenticateMediaBuyerOrLead()),
    keitaro_service: KeitaroService = Depends(get_keitaro_service),
    keitaro_config: dict = Depends(get_keitaro_config),
    db_repo=Depends(DatabaseRepositoryStub),
):
    username = await get_username_for_campaigns(user_id, keitaro_config["username"], db_repo.user)
    return await keitaro_service.get_user_campaigns(username)


@router.get("/campaign/streams", response_model=KeitaroStreamsResponse)
async def get_campaign_streams(
    campaign_id: int,
    user_id: Optional[int] = Query(None, description="User ID to get Keitaro config for (admin only)"),
    current_user: User = Depends(AuthenticateMediaBuyerOrLead()),
    keitaro_service: KeitaroService = Depends(get_keitaro_service),
):
    return await keitaro_service.get_campaign_streams(campaign_id)


@router.post("/stream/adname", response_model=CreativeResponseSchema)
async def add_adname_to_stream(
    adname_data: KeitaroAddAdnameSchema,
    current_user: User = Depends(AuthenticateMediaBuyerOrLead()),
    db_repo=Depends(DatabaseRepositoryStub),
):
    creative = await db_repo.creative.get_creative_by_id(adname_data.creative_id)
    user_id_to_use, user_id_to_save = resolve_user_id_for_creative(creative, adname_data.user_id, current_user.id)

    target_user = await resolve_keitaro_config_user(current_user, user_id_to_use, db_repo)
    keitaro_config = await db_repo.keitaro.get_user_keitaro_config(target_user)
    keitaro_service = KeitaroService(keitaro_config=keitaro_config)

    return await keitaro_service.add_adname_to_stream(
        adname_data.campaign_id, adname_data.stream_id, adname_data.creative_id, db_repo, user_id_to_save
    )


@router.delete("/stream/adname", response_model=CreativeResponseSchema)
async def remove_adname_from_stream(
    adname_data: KeitaroRemoveAdnameSchema,
    current_user: User = Depends(AuthenticateMediaBuyerOrLead()),
    db_repo=Depends(DatabaseRepositoryStub),
):
    creative = await db_repo.creative.get_creative_by_id(adname_data.creative_id)

    user_id_to_use = creative.keitaro_config_user_id if creative.keitaro_config_user_id is not None else current_user.id

    target_user = await resolve_keitaro_config_user(current_user, user_id_to_use, db_repo)
    keitaro_config = await db_repo.keitaro.get_user_keitaro_config(target_user)
    keitaro_service = KeitaroService(keitaro_config=keitaro_config)

    return await keitaro_service.remove_adname_from_stream(adname_data.stream_id, adname_data.creative_id, db_repo)
