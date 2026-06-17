from enum import StrEnum


class AnnotationType(StrEnum):
    MODIFIED = "modified"
    ADDED = "added"
    REMOVED = "removed"
