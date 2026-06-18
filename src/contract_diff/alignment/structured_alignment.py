from __future__ import annotations

from difflib import SequenceMatcher

from contract_diff.alignment.models.structured_block_match import BlockMatch
from contract_diff.extraction.structured.models import TextBlock
from contract_diff.extraction.structured.structured_pdf_reader import (
    normalize_for_alignment,
)

MODIFIED_BLOCK_SIMILARITY_THRESHOLD = 0.75


def align_structured_blocks(
    original_blocks: list[TextBlock],
    revised_blocks: list[TextBlock],
) -> list[BlockMatch]:
    """Align processed document blocks across the whole document."""

    original_normalized = [_normalized_block_text(block) for block in original_blocks]
    revised_normalized = [_normalized_block_text(block) for block in revised_blocks]

    matcher = SequenceMatcher(None, original_normalized, revised_normalized)
    matches: list[BlockMatch] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        original_segment = original_blocks[i1:i2]
        revised_segment = revised_blocks[j1:j2]

        if tag == "equal":
            matches.extend(
                _equal_match(original_block, revised_block)
                for original_block, revised_block in zip(
                    original_segment, revised_segment, strict=True
                )
            )
            continue

        if tag == "delete":
            matches.extend(_delete_match(block) for block in original_segment)
            continue

        if tag == "insert":
            matches.extend(_insert_match(block) for block in revised_segment)
            continue

        if tag == "replace":
            matches.extend(
                _align_replacement_segment(original_segment, revised_segment)
            )

    return matches


def _align_replacement_segment(
    original_blocks: list[TextBlock],
    revised_blocks: list[TextBlock],
) -> list[BlockMatch]:
    remaining_revised = list(revised_blocks)
    matches: list[BlockMatch] = []

    for original_block in original_blocks:
        best_index: int | None = None
        best_similarity = 0.0

        for revised_index, revised_block in enumerate(remaining_revised):
            similarity = _block_similarity(original_block, revised_block)

            if similarity > best_similarity:
                best_index = revised_index
                best_similarity = similarity

        if (
            best_index is not None
            and best_similarity >= MODIFIED_BLOCK_SIMILARITY_THRESHOLD
        ):
            revised_block = remaining_revised.pop(best_index)
            matches.append(
                _replace_match(original_block, revised_block, best_similarity)
            )
        else:
            matches.append(_delete_match(original_block))

    matches.extend(_insert_match(block) for block in remaining_revised)
    return matches


def _equal_match(original_block: TextBlock, revised_block: TextBlock) -> BlockMatch:
    return BlockMatch(
        original_block_id=_block_id(original_block),
        revised_block_id=_block_id(revised_block),
        operation="equal",
        similarity=1.0,
        original_text=original_block.text,
        revised_text=revised_block.text,
        original_page_index=original_block.page_index,
        revised_page_index=revised_block.page_index,
        original_block_index=original_block.block_index,
        revised_block_index=revised_block.block_index,
        original_bbox=original_block.bbox,
        revised_bbox=revised_block.bbox,
        section_path=_combined_section_path(original_block, revised_block),
    )


def _replace_match(
    original_block: TextBlock,
    revised_block: TextBlock,
    similarity: float,
) -> BlockMatch:
    return BlockMatch(
        original_block_id=_block_id(original_block),
        revised_block_id=_block_id(revised_block),
        operation="replace",
        similarity=similarity,
        original_text=original_block.text,
        revised_text=revised_block.text,
        original_page_index=original_block.page_index,
        revised_page_index=revised_block.page_index,
        original_block_index=original_block.block_index,
        revised_block_index=revised_block.block_index,
        original_bbox=original_block.bbox,
        revised_bbox=revised_block.bbox,
        section_path=_combined_section_path(original_block, revised_block),
    )


def _delete_match(original_block: TextBlock) -> BlockMatch:
    return BlockMatch(
        original_block_id=_block_id(original_block),
        revised_block_id=None,
        operation="delete",
        similarity=0.0,
        original_text=original_block.text,
        revised_text=None,
        original_page_index=original_block.page_index,
        revised_page_index=None,
        original_block_index=original_block.block_index,
        original_bbox=original_block.bbox,
        section_path=original_block.section_path,
    )


def _insert_match(revised_block: TextBlock) -> BlockMatch:
    return BlockMatch(
        original_block_id=None,
        revised_block_id=_block_id(revised_block),
        operation="insert",
        similarity=0.0,
        original_text=None,
        revised_text=revised_block.text,
        original_page_index=None,
        revised_page_index=revised_block.page_index,
        revised_block_index=revised_block.block_index,
        revised_bbox=revised_block.bbox,
        section_path=revised_block.section_path,
    )


def _block_similarity(original_block: TextBlock, revised_block: TextBlock) -> float:
    return SequenceMatcher(
        None,
        _normalized_block_text(original_block),
        _normalized_block_text(revised_block),
    ).ratio()


def _normalized_block_text(block: TextBlock) -> str:
    return normalize_for_alignment(block.normalized_text or block.text)


def _block_id(block: TextBlock) -> str:
    return f"page-{block.page_index}-block-{block.block_index}"


def _combined_section_path(
    original_block: TextBlock,
    revised_block: TextBlock,
) -> list[str]:
    if revised_block.section_path:
        return revised_block.section_path

    return original_block.section_path
