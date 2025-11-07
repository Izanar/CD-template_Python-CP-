from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DesignerTaskDifficultiesIds(BaseModel):
    id: int | None


class CreateTaskDifficultyDesignerSchema(BaseModel):
    name: str
    points: int


class TaskDifficultyDesignerResponseSchema(CreateTaskDifficultyDesignerSchema):
    id: int


class UpdateTaskDifficultyDesignerSchema(BaseModel):
    name: str | None = None
    points: int | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class TaskDifficultyDesignerSchema(BaseModel):
    id: int | None
    name: str | None
    points: int | None


class DesignerLoadTaskSchema(BaseModel):
    id: int
    username: str
    created_at: datetime
    role: str
    assigned_tasks_count: int

    model_config = ConfigDict(from_attributes=True)


class DesignerShortResponseSchema(BaseModel):
    id: int
    username: str
    created_at: datetime
    role: str

    model_config = ConfigDict(from_attributes=True)
