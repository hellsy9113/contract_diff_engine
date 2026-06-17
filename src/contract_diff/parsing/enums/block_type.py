from enum import StrEnum


class BlockType(StrEnum):
    HEADING = "heading"
    CLAUSE = "clause"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    DEFINITION = "definition"
    PAGE_ARTIFACT = "page_artifact"
    UNKNOWN = "unknown"
