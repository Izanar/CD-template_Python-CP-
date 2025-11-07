from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums.media_buyer_team_verticals import VerticalType


class BaseUserResponseSchema(BaseModel):
    id: int
    username: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MediaBuyerTeamResponseSchema(BaseModel):
    id: int
    name: str
    lead_id: int | None = None
    responsible_designer_id: int | None = None
    responsible_web_master_id: int | None = None
    has_keitaro_config: bool = False

    model_config = ConfigDict(from_attributes=True)


class MediaBuyerTeamMembersResponseSchema(BaseModel):
    id: int
    username: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MediaBuyerTeamDetailsResponseSchema(BaseModel):
    id: int
    name: str
    lead_id: int | None = None
    responsible_designer_id: int | None = None
    responsible_web_master_id: int | None = None
    has_keitaro_config: bool = False
    # TODO: lead_id: int - Uncomment when lead_id is added to the model
    members: list[MediaBuyerTeamMembersResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class CreateMediaBuyerTeamSchema(BaseModel):
    name: str
    vertical: VerticalType = VerticalType.CRYPTO
    prefix: str
    custom_task_start_id: int | None = Field(default=1)
    allow_archives: bool | None = None


class UpdateMediaBuyerTeamSchema(BaseModel):
    name: str | None = None
    prefix: str | None = None
    custom_task_start_id: int | None = None
    vertical: VerticalType | None = None
    allow_archives: bool | None = None


class AddResponsibleWebMasterSchema(BaseModel):
    team_id: int
    responsible_web_master_id: int


class AddMediaBuyerLeadSchema(BaseModel):
    team_id: int
    media_buyer_lead_id: int


class MediaBuyerTeamDetailResponseSchema(BaseModel):
    id: int
    name: str
    vertical: VerticalType
    prefix: str | None = None
    custom_task_start_id: int | None = None
    responsible_designer_user: BaseUserResponseSchema | None = None
    responsible_web_master_user: BaseUserResponseSchema | None = None
    lead_user: BaseUserResponseSchema | None = None
    members_list: list[MediaBuyerTeamMembersResponseSchema]
    allow_archives: bool | None = None
    has_keitaro_config: bool = False

    model_config = ConfigDict(from_attributes=True)


class MediaBuyerShortResponseSchema(BaseModel):
    id: int
    username: str | None = None
    created_at: datetime | None = None
    role: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MediaBuyerTeamStatistic(BaseModel):
    team_id: int
    team_name: str
    vertical: VerticalType
    waiting_to_assign: int = 0
    waiting_to_start: int = 0
    in_progress: int = 0
    requested_changes: int = 0
    under_tl_review: int = 0
    under_buyer_review: int = 0


class MediaBuyerVerticalStatistic(BaseModel):
    vertical: VerticalType
    teams: list[MediaBuyerTeamStatistic]


class MediaBuyerTeamShortResponseSchema(BaseModel):
    id: int
    team_name: str
