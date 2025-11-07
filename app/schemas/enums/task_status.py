import enum
from typing import Literal

from app.schemas.enums.user import UserRole


class DesignerTaskStatus(enum.Enum):
    DRAFT = "draft"
    WAITING_TO_ASSIGN = "waiting_to_assign"
    WAITING_TO_START = "waiting_to_start"
    IN_PROGRESS = "in_progress"
    REQUESTED_CHANGES = "requested_changes"
    UNDER_TL_REVIEW = "under_tl_review"
    UNDER_BUYER_REVIEW = "under_buyer_review"
    COMPLETED = "completed"


class WebMasterTaskStatus(enum.Enum):
    DRAFT = "draft"
    WAITING_TO_ASSIGN = "waiting_to_assign"
    WAITING_TO_START = "waiting_to_start"
    IN_PROGRESS = "in_progress"
    REQUESTED_CHANGES = "requested_changes"
    UNDER_TL_REVIEW = "under_tl_review"
    UNDER_BUYER_REVIEW = "under_buyer_review"
    COMPLETED = "completed"


role_allowed_web_master_task_statuses: dict[UserRole, list[WebMasterTaskStatus] | Literal["all"]] = {
    UserRole.admin: "all",
    UserRole.media_buyer: [WebMasterTaskStatus.COMPLETED, WebMasterTaskStatus.UNDER_TL_REVIEW],
    UserRole.lead_web_master: [
        WebMasterTaskStatus.WAITING_TO_START,
        WebMasterTaskStatus.IN_PROGRESS,
        WebMasterTaskStatus.UNDER_TL_REVIEW,
        WebMasterTaskStatus.UNDER_BUYER_REVIEW,
        WebMasterTaskStatus.REQUESTED_CHANGES,
    ],
    UserRole.web_master: [
        WebMasterTaskStatus.WAITING_TO_START,
        WebMasterTaskStatus.IN_PROGRESS,
        WebMasterTaskStatus.UNDER_TL_REVIEW,
    ],
    UserRole.designer: [],
    UserRole.user: [],
    UserRole.lead_designer: [],
    UserRole.lead_media_buyer: [],
}
