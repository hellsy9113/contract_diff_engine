from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from contract_diff.alignment.models.structured_block_match import BlockMatch
from contract_diff.comparison.token_diff import get_revised_changed_fragments
from contract_diff.extraction.structured.models import BoundingBox

ChangeType = Literal[
    "added",
    "deleted",
    "modified",
    "moved",
    "format_changed",
    "table_cell_modified",
    "uncertain",
]


class Location(BaseModel):
    """Structured document location for a change endpoint."""

    model_config = ConfigDict(frozen=True)

    page_index: int
    block_index: int | None
    bbox: BoundingBox | None
    section_path: list[str]


class Change(BaseModel):
    """Renderer-ready structured change emitted by comparison."""

    model_config = ConfigDict(frozen=True)

    change_id: str
    change_type: ChangeType
    original_text: str | None
    revised_text: str | None
    original_location: Location | None
    revised_location: Location | None
    changed_fragments: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
    section_path: list[str]
    metadata: dict[str, Any]


def build_changes_from_alignment(matches: list[BlockMatch]) -> list[Change]:
    """Convert block alignment decisions into structured renderer input."""

    changes: list[Change] = []

    for match in matches:
        if match.operation == "equal":
            continue

        change_type = _change_type_for_operation(match.operation)
        changed_fragments: list[str] = []

        if (
            change_type == "modified"
            and match.original_text is not None
            and match.revised_text is not None
        ):
            changed_fragments = get_revised_changed_fragments(
                match.original_text,
                match.revised_text,
            )

        changes.append(
            Change(
                change_id=_change_id(len(changes) + 1),
                change_type=change_type,
                original_text=match.original_text,
                revised_text=match.revised_text,
                original_location=_original_location(match),
                revised_location=_revised_location(match),
                changed_fragments=changed_fragments,
                confidence=_confidence_for_match(match),
                section_path=match.section_path,
                metadata={
                    "alignment_operation": match.operation,
                    "similarity": match.similarity,
                    "original_block_id": match.original_block_id,
                    "revised_block_id": match.revised_block_id,
                },
            )
        )

    return changes


def _change_type_for_operation(operation: str) -> ChangeType:
    if operation == "insert":
        return "added"

    if operation == "delete":
        return "deleted"

    if operation == "replace":
        return "modified"

    if operation == "move":
        return "moved"

    return "uncertain"


def _original_location(match: BlockMatch) -> Location | None:
    if match.original_page_index is None:
        return None

    return Location(
        page_index=match.original_page_index,
        block_index=match.original_block_index,
        bbox=match.original_bbox,
        section_path=match.section_path,
    )


def _revised_location(match: BlockMatch) -> Location | None:
    if match.revised_page_index is None:
        return None

    return Location(
        page_index=match.revised_page_index,
        block_index=match.revised_block_index,
        bbox=match.revised_bbox,
        section_path=match.section_path,
    )


def _confidence_for_match(match: BlockMatch) -> float:
    if match.operation == "uncertain":
        return min(match.similarity, 0.5)

    if match.operation == "replace":
        return match.similarity

    if match.operation in {"insert", "delete", "move"}:
        return 1.0

    return match.similarity


def _change_id(index: int) -> str:
    return f"CHG-{index:04d}"
