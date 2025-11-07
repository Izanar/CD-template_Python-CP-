from pydantic import BaseModel


class DesignerStatisticShortResponseSchema(BaseModel):
    id: int
    username: str
    user_role: str


class DesignerTeamShortResponseSchema(BaseModel):
    id: int
    team_name: str


class DesignerStatistic(BaseModel):
    designer: DesignerStatisticShortResponseSchema
    designer_team: DesignerTeamShortResponseSchema | None = None
    waiting_to_start_count: int | None = 0
    in_progress_count: int | None = 0
    requested_changes_count: int | None = 0
    under_tl_review_count: int | None = 0
    under_buyer_review_count: int | None = 0
    completed_count: int | None = 0


class DesignerPointsStatistic(BaseModel):
    designer: DesignerStatisticShortResponseSchema
    designer_team: DesignerTeamShortResponseSchema | None = None
    completed_tasks: int | None = 0
    total_points: int | None = 0
    mean_rating: float | None = None


class OperationalTasksStatistic(BaseModel):
    waiting_to_assign: int | None = 0
    waiting_to_start: int | None = 0
    in_progress: int | None = 0
    requested_changes: int | None = 0
    under_tl_review: int | None = 0
    completed: int | None = 0
