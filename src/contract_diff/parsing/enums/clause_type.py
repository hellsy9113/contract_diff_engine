from enum import StrEnum


class ClauseType(StrEnum):
    STANDARD = "standard"
    NESTED = "nested"
    DEFINITION = "definition"
