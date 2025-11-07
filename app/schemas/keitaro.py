from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, RootModel


class KeitaroUserSearchSchema(BaseModel):
    username: str = Field(..., description="Username пользователя для поиска в Keitaro")


class KeitaroUserCampaignsResponse(RootModel[List[Dict[str, Any]]]):
    root: List[Dict[str, Any]]


class KeitaroCampaignStreamsSchema(BaseModel):
    campaign_id: int = Field(..., description="ID кампании для получения потоков")


class KeitaroStreamResponse(BaseModel):
    id: int
    name: str


class KeitaroStreamsResponse(RootModel[List[KeitaroStreamResponse]]):
    root: List[KeitaroStreamResponse]


class KeitaroAddAdnameSchema(BaseModel):
    campaign_id: int = Field(..., description="ID кампании")
    stream_id: int = Field(..., description="ID потока")
    creative_id: int = Field(..., description="ID креатива")
    user_id: Optional[int] = Field(None, description="User ID to get Keitaro config for (admin only)")


class KeitaroRemoveAdnameSchema(BaseModel):
    stream_id: int = Field(..., description="ID потока")
    creative_id: int = Field(..., description="ID креатива")


class StreamUpdateResult(BaseModel):
    stream_id: int
    success: bool
    error: Optional[str] = None
