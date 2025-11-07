from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.enums.user import UserRole
from app.schemas.media_buyers.tasks.designer_tasks import DesignerCreatedByResponseSchema


class ChangedByUserSchema(DesignerCreatedByResponseSchema):
    role: UserRole


class DesignerTaskHistoryResponseSchema(BaseModel):
    id: int
    task_id: int
    event: str
    event_info: str
    description: str | None
    changed_at: datetime
    changed_by: ChangedByUserSchema | None
    time_since_previous: float | None

    class Config:
        from_attributes = True


class WebMasterTaskHistoryResponseSchema(BaseModel):
    id: int
    task_id: int
    buyer: str | None = None
    lead: str | None = None
    assigned_web_master: str | None = None
    event: str
    event_info: str

    model_config = ConfigDict(from_attributes=True)
