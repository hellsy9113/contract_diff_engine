from enum import StrEnum


class AlignmentStatus(StrEnum):
    MATCHED = "matched"
    ORIGINAL_ONLY = "original_only"
    REVISED_ONLY = "revised_only"
