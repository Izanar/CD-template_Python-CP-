from typing import List

from pydantic import BaseModel, ConfigDict

from app.schemas.creative import CreativeCreateWithoutTaskSchema
from app.schemas.enums.task_type import DesignerTaskTypeEnum
from app.schemas.enums.web_master_task import WebMasterProjectType
from app.schemas.media_buyer_team import MediaBuyerTeamShortResponseSchema
from app.schemas.user import User


class MediaBuyerTaskCreateSchema(BaseModel):
    description: str | None = None
    task_type: DesignerTaskTypeEnum | None = None
    geo_id: int | None = None
    language_id: int | None = None
    celebrities: list[int] | None = None
    description_files: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class MediaBuyerTaskWithCreativesCreateSchema(MediaBuyerTaskCreateSchema):
    creatives: List[CreativeCreateWithoutTaskSchema] = []


class WebMasterTaskCreateSchema(MediaBuyerTaskCreateSchema):
    project_type: WebMasterProjectType | None = None
    funnel_id: int | None = None
    site_name_id: int | None = None
    celebrity_id: int | None = None


class MediaBuyerTaskUpdateSchema(MediaBuyerTaskCreateSchema):
    is_high_priority: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class MediaBuyerStatisticsSchema(BaseModel):
    user: User
    tasks_created: int
    tasks_completed: int
    mean_rating: float = 0
    team: MediaBuyerTeamShortResponseSchema | None = None

    @classmethod
    def from_stats(cls, designer_stats, webmaster_stats) -> list["MediaBuyerStatisticsSchema"]:
        webmaster_stats_map = {stat["id"]: stat for stat in webmaster_stats}
        return [
            cls(
                user={
                    "id": designer_stat["id"],
                    "username": designer_stat["name"],
                },
                tasks_created=designer_stat["tasks_created"]
                + webmaster_stats_map.get(designer_stat["id"], {"tasks_created": 0})["tasks_created"],
                tasks_completed=designer_stat["tasks_completed"]
                + webmaster_stats_map.get(designer_stat["id"], {"tasks_completed": 0})["tasks_completed"],
                mean_rating=designer_stat["mean_rating"] or 0,
                team=(
                    MediaBuyerTeamShortResponseSchema(
                        id=designer_stat["team_id"],
                        team_name=designer_stat["team_name"],
                        has_keitaro_config=designer_stat.get("has_keitaro_config", False),
                    )
                    if designer_stat.get("team_id") is not None
                    else None
                ),
            )
            for designer_stat in designer_stats
        ]


class SetAssistantSchema(BaseModel):
    teacher_id: int
    assistant_id: int

    model_config = ConfigDict(from_attributes=True)
