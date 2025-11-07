from enum import Enum


class CreativeFormat(str, Enum):
    SQUARE = "square"
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    OTHER = "other"
    RATIO_5_TO_4 = "ratio_5_to_4"
    RATIO_4_TO_5 = "ratio_4_to_5"
