from __future__ import annotations

from contract_diff.extraction.structured.models import (
    ExtractedPage,
    StructuredDocument,
    TextBlock,
)
from contract_diff.extraction.structured.reading_order import resolve_reading_order

COLUMN_GAP_RATIO = 0.18
MIN_BLOCKS_FOR_TWO_COLUMNS = 4
NON_BODY_BLOCK_TYPES = {"header", "footer", "noise"}


def detect_columns_for_page(
    blocks: list[TextBlock],
    page_width: float,
) -> dict[int, int]:
    body_blocks = [
        block
        for block in blocks
        if block.block_type not in NON_BODY_BLOCK_TYPES and block.normalized_text
    ]

    if len(body_blocks) < MIN_BLOCKS_FOR_TWO_COLUMNS:
        return {block.block_index: 0 for block in body_blocks}

    ordered = sorted(body_blocks, key=lambda block: block.bbox.x0)
    gaps = [
        (right.bbox.x0 - left.bbox.x0, left.bbox.x0, right.bbox.x0)
        for left, right in zip(ordered, ordered[1:])
    ]
    largest_gap, gap_left, gap_right = max(gaps, default=(0.0, 0.0, 0.0))

    if largest_gap < page_width * COLUMN_GAP_RATIO:
        return {block.block_index: 0 for block in body_blocks}

    split_x = (gap_left + gap_right) / 2.0
    left_blocks = [block for block in body_blocks if block.bbox.x0 <= split_x]
    right_blocks = [block for block in body_blocks if block.bbox.x0 > split_x]

    if not left_blocks or not right_blocks:
        return {block.block_index: 0 for block in body_blocks}

    if _columns_overlap_too_much(left_blocks, right_blocks):
        return {block.block_index: 0 for block in body_blocks}

    return {
        block.block_index: 0 if block in left_blocks else 1 for block in body_blocks
    }


def apply_column_detection(document: StructuredDocument) -> StructuredDocument:
    pages: list[ExtractedPage] = []

    for page in document.pages:
        column_indexes = detect_columns_for_page(page.blocks, page.width)
        blocks: list[TextBlock] = []

        for block in page.blocks:
            if block.block_index in column_indexes:
                blocks.append(
                    block.model_copy(
                        update={"column_index": column_indexes[block.block_index]}
                    )
                )
            else:
                blocks.append(block.model_copy(update={"column_index": None}))

        pages.append(page.model_copy(update={"blocks": blocks}))

    updated_document = document.model_copy(update={"pages": pages})
    return resolve_reading_order(updated_document)


def _columns_overlap_too_much(
    left_blocks: list[TextBlock],
    right_blocks: list[TextBlock],
) -> bool:
    left_max_x1 = max(block.bbox.x1 for block in left_blocks)
    right_min_x0 = min(block.bbox.x0 for block in right_blocks)
    return left_max_x1 > right_min_x0
