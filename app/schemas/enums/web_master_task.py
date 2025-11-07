from enum import Enum


class WebMasterProjectType(str, Enum):
    PROKLALAND = "proklaland"
    PRELAND = "preland"
    LAND = "land"
    QUIZ = "quiz"
    WHITE = "white"
    CAMPAIGN_WHITE = "campaign_white"
    PRELAND_LAND = "preland_land"
    OTHER = "other"
