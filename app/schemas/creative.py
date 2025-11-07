import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.enums.creative_approach import CreativeApproach
from app.schemas.enums.creative_format import CreativeFormat
from app.schemas.media_file import MediaFileResponseSchema
from app.schemas.user import KeitaroConfigUserSchema


class CampaignInfo(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None


class StreamInfo(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None


class CreativeResponseSchema(BaseModel):
    id: int
    task_id: int
    format: Optional[CreativeFormat] = None
    subtitles: Optional[bool] = None
    plashka: Optional[bool] = None
    text: Optional[str] = None
    ad_name: Optional[str] = None
    campaign: Optional[CampaignInfo] = None
    streams: List[StreamInfo] = []
    approaches: List[str] = Field(alias="approaches", default_factory=list)
    keitaro_config_user: Optional[KeitaroConfigUserSchema] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    media_files: List[MediaFileResponseSchema] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CreativeCreateSchema(BaseModel):
    task_id: int
    format: Optional[CreativeFormat] = None
    subtitles: Optional[bool] = None
    plashka: Optional[bool] = None
    text: Optional[str] = None


class CreativeCreateWithoutTaskSchema(BaseModel):
    format: Optional[CreativeFormat] = None
    text: Optional[str] = None
    subtitles: Optional[bool] = None
    plashka: Optional[bool] = None


class CreativeUpdateSchema(BaseModel):
    format: Optional[CreativeFormat] = None
    subtitles: Optional[bool] = None
    plashka: Optional[bool] = None
    text: Optional[str] = None
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    streams_data: Optional[List[Dict[str, Any]]] = None
    approaches: Optional[List[CreativeApproach]] = None
    ad_name: Optional[str] = None
    keitaro_config_user_id: Optional[int] = None
    model_config = ConfigDict(extra="forbid")

    @field_validator("ad_name")
    @classmethod
    def validate_ad_name(cls, v) -> str | None:
        if v is not None:
            if not re.match(r"^[a-zA-Z0-9_]+$", v):
                raise ValueError(
                    "Ad name must contain only English letters, numbers and underscores [a-z, A-Z, 0-9, _]"
                )
            if len(v) < 1 or len(v) > 50:
                raise ValueError("Ad name must be between 1 and 50 characters long")
        return v


class CreativeCRMResponseSchema(BaseModel):
    id: int
    ad_name: str
    approaches: str
    celebrities: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CreativeSearchRequestSchema(BaseModel):
    ad_name: str
