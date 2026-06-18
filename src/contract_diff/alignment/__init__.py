"""Deterministic alignment layer."""

from contract_diff.alignment.structured_alignment import (
    MODIFIED_BLOCK_SIMILARITY_THRESHOLD,
    align_structured_blocks,
)

__all__ = [
    "MODIFIED_BLOCK_SIMILARITY_THRESHOLD",
    "align_structured_blocks",
]
