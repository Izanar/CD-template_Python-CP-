from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.enums.web_master_task import WebMasterProjectType
from app.schemas.lead_web_master import TaskDifficultyWebMasterSchema, WebMasterTaskDifficultiesIds
from app.schemas.media_buyers.tasks.designer_tasks import CelebrityResponseSchema, GeoResponseSchema


class UpdateWebMasterTaskSchema(BaseModel):
    task_id: int
    assigned_to_id: int | None = None
    difficulty_ids: list[WebMasterTaskDifficultiesIds] | None = None
    deadline: datetime | None = None
    is_high_priority: bool | None = None


class WebMasterTaskEditSchema(BaseModel):
    id: int
    description: str
    created_at: datetime
    solved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class WebMasterTaskTypeCreateSchema(BaseModel):
    name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WebMasterTaskTypeResponseSchema(BaseModel):
    id: int | None
    name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskTypeSchema(BaseModel):
    id: int | None
    name: str | None = None


class WebMasterMediaFilesResponseSchema(BaseModel):
    id: int
    file_url: str


class WebMasterAssignedToResponseSchema(BaseModel):
    id: int
    username: str
    team_id: int | None = None


class WebMasterCreatedByResponseSchema(BaseModel):
    id: int
    username: str


class WebMasterTaskResponseSchema(BaseModel):
    id: int | None = None
    title: str | None = None
    description: str | None = None
    task_type: TaskTypeSchema | None = None
    task_status: str | None = None
    difficulties: list[TaskDifficultyWebMasterSchema] | None = []
    created_at: datetime | None = None
    assigned_to_user: WebMasterAssignedToResponseSchema | None = None
    deadline: datetime | None = None
    media_files_info: list[WebMasterMediaFilesResponseSchema] | None = None
    is_high_priority: bool | None = None
    edits: list[WebMasterTaskEditSchema] | None = []

    geo: GeoResponseSchema | None = None
    vertical: VerticalType | None = None
    is_deleted: bool | None = None
    funnel: CelebrityResponseSchema | None = None
    site_name: CelebrityResponseSchema | None = None
    celebrity: CelebrityResponseSchema | None = None
    project_type: WebMasterProjectType | None = None

    model_config = ConfigDict(from_attributes=True)


class WebMasterTaskResponseSchemaWithCreator(WebMasterTaskResponseSchema):
    created_by_user: WebMasterCreatedByResponseSchema | None = None


class WebMasterPointsRequest(BaseModel):
    user_id: int | None = None
    team_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def set_defaults(self) -> "WebMasterPointsRequest":
        today = date.today()
        default_start = date(today.year, today.month, 1)
        if self.start_date is None:
            self.start_date = default_start
        if self.end_date is None:
            self.end_date = today
        return self


class WebMasterUserPointsResponse(BaseModel):
    user_id: int
    completed_tasks: int
    total_points: int = 0

    model_config = ConfigDict(from_attributes=True)


class WebMasterTaskEditRequestSchema(BaseModel):
    description: str


class ApproveWebMasterTaskEditSchema(BaseModel):
    task_id: int
    edit_id: int


class WebMasterTaskEditsResponseSchema(BaseModel):
    id: int | None
    task_id: int | None
    description: str | None = None
    solved_at: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class WebMasterTaskDeleteResponseSchema(BaseModel):
    task_id: int
    message: str = "Task was deleted successfully"
