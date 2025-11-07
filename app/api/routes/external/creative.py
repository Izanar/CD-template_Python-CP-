from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependecies.external_api import verify_external_api_key
from app.dependecies.stub import DatabaseRepositoryStub
from app.repository.database.base import DatabaseRepository
from app.schemas.creative import CreativeCRMResponseSchema, CreativeSearchRequestSchema

from .utils import format_creative_for_crm

creative_router = APIRouter(
    prefix="/creative",
)


@creative_router.post(
    "",
    response_model=CreativeCRMResponseSchema,
    summary="Get creative by ad_name for external systems",
)
async def get_creative_by_ad_name(
    request: CreativeSearchRequestSchema,
    db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
    api_key: Annotated[str, Depends(verify_external_api_key)],
):
    creative = await db_repo.creative.get_creative_by_ad_name(request.ad_name)
    formatted_data = format_creative_for_crm(creative)
    return CreativeCRMResponseSchema(**formatted_data)
