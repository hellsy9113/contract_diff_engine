from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from contract_diff.extraction.structured.models import BoundingBox

BlockAlignmentOperation = Literal[
    "equal",
    "insert",
    "delete",
    "replace",
    "move",
    "uncertain",
]


class BlockMatch(BaseModel):
    """One structured block alignment decision."""

    model_config = ConfigDict(frozen=True)

    original_block_id: str | None
    revised_block_id: str | None
    operation: BlockAlignmentOperation
    similarity: float = Field(ge=0.0, le=1.0)
    original_text: str | None
    revised_text: str | None
    original_page_index: int | None
    revised_page_index: int | None
    original_block_index: int | None = None
    revised_block_index: int | None = None
    original_bbox: BoundingBox | None = None
    revised_bbox: BoundingBox | None = None
    section_path: list[str]
