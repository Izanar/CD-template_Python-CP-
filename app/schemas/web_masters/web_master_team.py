from typing import List

from pydantic import BaseModel, ConfigDict


class CreateWebMasterTeamSchema(BaseModel):
    team_name: str


class WebMasterTeamSchema(BaseModel):
    id: int
    name: str
    lead_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class WebMasterTeamMembersResponseSchema(BaseModel):
    id: int

    model_config = ConfigDict(from_attributes=True)


class WebMasterTeamDetailsSchema(BaseModel):
    id: int
    name: str
    lead_id: int | None = None
    members: List[WebMasterTeamMembersResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class UpdateWebMasterTeamSchema(BaseModel):
    id: int | None = None
    name: str | None = None
    lead_id: int | None = None


class AddLeadWebMasterTeamSchema(BaseModel):
    team_id: int
    lead_id: int


class WebMasterTeamShortResponseSchema(BaseModel):
    id: int
    team_name: str
