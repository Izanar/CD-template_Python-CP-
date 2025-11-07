from enum import Enum


class CreativeApproach(str, Enum):
    ARREST = "arrest"
    CRY = "cry"
    CHECK = "check"
    CHARGES = "charges"
    ANTI_SCAM = "anti_scam"
    GUARANTEE_FROM_GOVERNMENT = "guarantee_from_government"
    EARNING_PLATFORM = "earning_platform"
    EXPOSED = "exposed"
    CONFLICT = "conflict"
    SCAM = "scam"
    INTERVIEW = "interview"
    ATM_QUEUE = "atm_queue"
    COUNTER = "counter"
    CRISIS = "crisis"
    LIVE = "live"
    CONFERENCE_CALL = "conference_call"

    @classmethod
    def get_ordered_values(cls) -> list[str]:
        return [approach.value for approach in cls]

    @classmethod
    def sort_approaches(cls, approaches: list[str]) -> list[str]:
        ordered_values = cls.get_ordered_values()
        return [approach for approach in ordered_values if approach in approaches]
