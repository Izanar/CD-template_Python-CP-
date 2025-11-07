from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.enums.user import UserRole


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    username: str | None = None


class LogoutRequest(BaseModel):
    user_id: int


class User(BaseModel):
    id: int
    username: str


class UserCreateSchema(BaseModel):
    role: UserRole
    username: str
    password: str
    allow_view_team_tasks: bool | None = None

    @field_validator("allow_view_team_tasks", mode="before")
    def check_allow_view_team_tasks(cls, v, values):
        if values.data.get("role") != UserRole.lead_media_buyer:
            return None
        return v if v is not None else False


class UserUpdateSchema(BaseModel):
    role: UserRole | None = None
    username: str | None = None
    password: str | None = None
    allow_view_team_tasks: bool | None = None


class TeamBase(BaseModel):
    id: int
    name: str


class UserResponseSchema(BaseModel):
    id: int | None = None
    role: UserRole | None = None
    username: str | None = None
    team: TeamBase | None = None
    created_at: datetime | None = None
    allow_view_team_tasks: bool | None = None
    vertical: VerticalType | None = None

    class Config:
        from_attributes = True

    @field_validator("team", mode="before")
    def rename_team_name(cls, value):
        if isinstance(value, dict) and "team_name" in value:
            return {"id": value["id"], "name": value["team_name"]}
        if hasattr(value, "id") and hasattr(value, "team_name"):
            return {"id": value.id, "name": value.team_name}
        return value


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    user: Optional[UserResponseSchema] = None


class KeitaroConfigUserSchema(BaseModel):
    id: int
    username: str | None = None

    class Config:
        from_attributes = True


class FullUserResponseSchema(BaseModel):
    id: Optional[int] = None
    role: Optional[UserRole] = None
    username: Optional[str] = None
    allow_view_team_tasks: bool | None = None
    created_at: Optional[datetime] = None
    team: Optional[TeamBase] = None
    media_buyer_teams: Optional[list[dict]] = None

    @model_validator(mode="before")
    def serialize_user(cls, values):
        user = values.get("user")
        if user:
            team = None
            media_buyer_teams = None

            if user.designer and user.designer.teams:
                first_team = user.designer.teams[0]
                team = {"id": first_team.id, "name": first_team.name}

            elif user.media_buyer and user.media_buyer.teams:
                first_team = user.media_buyer.teams[0]
                team = {"id": first_team.id, "name": first_team.name}

            if user.role == UserRole.lead_designer and hasattr(user.designer, "responsible_for_teams"):
                responsible_teams = user.designer.responsible_for_teams
                media_buyer_teams = (
                    [{"id": t.id, "name": t.name} for t in responsible_teams] if responsible_teams else None
                )

            values["id"] = user.id
            values["username"] = user.username
            values["role"] = user.role
            values["created_at"] = user.created_at
            values["allow_view_team_tasks"] = getattr(user, "allow_view_team_tasks", None)
            values["team"] = team
            values["media_buyer_teams"] = media_buyer_teams

        return values

    class Config:
        from_attributes = True
