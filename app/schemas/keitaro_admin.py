from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class KeitaroConfigCreateSchema(BaseModel):
    name: str
    api_key: str
    base_url: str
    creo: str


class KeitaroConfigUpdateSchema(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    creo: Optional[str] = None


class KeitaroConfigResponseSchema(BaseModel):
    id: int
    name: str
    base_url: str
    creo: str
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class MediaBuyerTeamMinimalSchema(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class AddKeitaroConfigToTeamSchema(BaseModel):
    team_id: int
    keitaro_config_id: int


class AddKeitaroConfigToTeamResponseSchema(BaseModel):
    config: KeitaroConfigResponseSchema
    team: MediaBuyerTeamMinimalSchema

    class Config:
        from_attributes = True
