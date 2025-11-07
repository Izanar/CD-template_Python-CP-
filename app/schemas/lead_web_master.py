from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WebMasterTaskDifficultiesIds(BaseModel):
    id: int | None


class CreateTaskDifficultyWebMasterSchema(BaseModel):
    name: str
    points: int


class TaskDifficultyWebMasterResponseSchema(CreateTaskDifficultyWebMasterSchema):
    id: int


class UpdateTaskDifficultyWebMasterSchema(BaseModel):
    name: str | None = None
    points: int | None = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class TaskDifficultyWebMasterSchema(BaseModel):
    id: int | None
    name: str | None
    points: int | None


class WebMasterLoadTaskSchema(BaseModel):
    id: int
    username: str
    created_at: datetime
    role: str
    assigned_tasks_count: int

    model_config = ConfigDict(from_attributes=True)


class WebMasterShortResponseSchema(BaseModel):
    id: int
    username: str
    created_at: datetime
    role: str

    model_config = ConfigDict(from_attributes=True)
