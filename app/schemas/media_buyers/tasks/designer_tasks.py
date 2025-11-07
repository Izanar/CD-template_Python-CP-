from datetime import date, datetime
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.creative import CreativeResponseSchema
from app.schemas.designers.lead_designer import DesignerTaskDifficultiesIds, TaskDifficultyDesignerSchema
from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.enums.task_type import DesignerTaskTypeEnum
from app.schemas.media_buyer_team import MediaBuyerTeamShortResponseSchema


class CelebrityResponseSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class PrimitiveResponseSchema(BaseModel):
    id: int
    name: str
    is_deleted: bool
    model_config = ConfigDict(from_attributes=True)


class UpdateDesignerTaskSchema(BaseModel):
    task_id: int
    assigned_to_id: int | None = None
    difficulty_ids: list[DesignerTaskDifficultiesIds] | None = None
    deadline: datetime | None = None
    is_high_priority: bool | None = None
    celebrities: list[int] | None = None


class DesignerTaskEditSchema(BaseModel):
    id: int
    description: str
    created_at: datetime
    solved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DesignerMediaFilesResponseSchema(BaseModel):
    id: int
    file_url: str


class DesignerAssignedToResponseSchema(BaseModel):
    id: int
    username: str
    team_id: int | None = None


class DesignerCreatedByResponseSchema(BaseModel):
    id: int
    username: str
    team: MediaBuyerTeamShortResponseSchema | None = None


class TaskEvaluationSchema(BaseModel):
    rating: int
    comment: str


class Note(BaseModel):
    user: str
    note: str


class GeoCreateSchema(BaseModel):
    code: str


class GeoResponseSchema(BaseModel):
    id: int
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class LanguageCreateSchema(BaseModel):
    name: str
    code: str


class LanguageResponseSchema(BaseModel):
    id: int
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class DesignerTaskResponseSchema(BaseModel):
    id: int | None
    uuid: UUID | None = None
    title: str | None = None
    description: str | None = None
    task_type: DesignerTaskTypeEnum | None = None
    task_status: str | None = None
    difficulties: list[TaskDifficultyDesignerSchema] | None = []
    geo: GeoResponseSchema | None = None
    language: LanguageResponseSchema | None = None
    celebrities: list[CelebrityResponseSchema] | None = Field(
        alias="celebrities_list", serialization_alias="celebrities"
    )
    created_at: datetime | None = None
    assigned_to_user: DesignerAssignedToResponseSchema | None = None
    deadline: datetime | None = None
    files: list[DesignerMediaFilesResponseSchema] | None = []
    description_files: list[DesignerMediaFilesResponseSchema] | None = []
    is_high_priority: bool | None = None
    edits: list[DesignerTaskEditSchema] | None = []
    is_operational: bool | None = False
    is_deleted: bool | None = False

    note: Optional[Union[str, List[Note]]] = None
    evaluations: list[TaskEvaluationSchema] | None = None

    evaluation_required: bool | None = None
    vertical: VerticalType | None = None
    allow_archives: bool | None = None

    time_spent_seconds: int | None = None
    creatives: List[CreativeResponseSchema] | None = []

    model_config = ConfigDict(from_attributes=True)


class DesignerTaskResponseSchemaWithCreator(DesignerTaskResponseSchema):
    created_by_user: DesignerCreatedByResponseSchema | None = None


class DesignerTaskEditRequestSchema(BaseModel):
    description: str


class ApproveDesignerTaskEditSchema(BaseModel):
    task_id: int
    edit_id: int


class DesignerTaskEditsResponseSchema(BaseModel):
    id: int | None
    task_id: int | None
    description: str | None = None
    solved_at: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DesignerTaskDeleteResponseSchema(BaseModel):
    task_id: int
    message: str = "Task was deleted successfully"


class DesignerPointsRequest(BaseModel):
    user_id: int | None = None
    team_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def set_defaults(self) -> "DesignerPointsRequest":
        today = date.today()
        default_start = date(today.year, today.month, 1)
        if self.start_date is None:
            self.start_date = default_start
        if self.end_date is None:
            self.end_date = today
        return self


class DesignerUserPointsResponse(BaseModel):
    user_id: int
    completed_tasks: int
    total_points: int = 0

    model_config = ConfigDict(from_attributes=True)


class CreateOperationDesignerTaskSchema(BaseModel):
    assigned_to_id: int | None = None
    task_type: DesignerTaskTypeEnum | None = None
    description: str
    difficulty_ids: list[DesignerTaskDifficultiesIds] | None = None
    deadline: datetime | None = None
    is_high_priority: bool | None = None


class ApproveTaskSchema(BaseModel):
    rating: int | None = None
    comment: str | None = None


class PrimitiveCreateSchema(BaseModel):
    name: str
