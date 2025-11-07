from typing import List

from pydantic import BaseModel, ConfigDict


class MediaFileKeysPayload(BaseModel):
    file_keys: List[str]


class MediaFileKeyUpdatePayload(BaseModel):
    file_id: int
    new_file_key: str


class MediaFileDeletePayload(BaseModel):
    file_ids: List[int]


class MediaFileResponseSchema(BaseModel):
    id: int
    file_url: str
    file_key: str | None = None
    is_description: bool = False

    model_config = ConfigDict(from_attributes=True)
