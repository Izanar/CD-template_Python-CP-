from typing import List

from pydantic import BaseModel, ConfigDict


class CreateDesignerTeamSchema(BaseModel):
    name: str


class DesignerTeamSchema(BaseModel):
    id: int
    name: str
    lead_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class DesignerTeamMembersResponseSchema(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class DesignerTeamDetailsSchema(BaseModel):
    id: int
    name: str
    lead_users: List[DesignerTeamMembersResponseSchema] | None = None
    members_list: List[DesignerTeamMembersResponseSchema] | None = []

    model_config = ConfigDict(from_attributes=True)


class UpdateDesignerTeamSchema(BaseModel):
    name: str | None = None


class UpdateDesignerTeamResponseSchema(UpdateDesignerTeamSchema):
    id: int | None = None


class AddLeadDesignerTeamSchema(BaseModel):
    team_id: int
    lead_id: list[int]


class CreateDesignersTeamsPayload(BaseModel):
    team_name: str
