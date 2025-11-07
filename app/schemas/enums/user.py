import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    media_buyer = "media_buyer"
    web_master = "web_master"
    user = "user"
    lead_web_master = "lead_web_master"
    lead_media_buyer = "lead_media_buyer"
    lead_designer = "lead_designer"
    designer = "designer"
