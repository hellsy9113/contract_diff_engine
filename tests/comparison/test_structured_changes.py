from __future__ import annotations

from contract_diff.alignment.models.structured_block_match import BlockMatch
from contract_diff.alignment.structured_alignment import align_structured_blocks
from contract_diff.comparison.structured_changes import build_changes_from_alignment
from contract_diff.extraction.structured.models import (
    BoundingBox,
    TextBlock,
    TextLine,
    TextSpan,
)
from contract_diff.extraction.structured.structured_pdf_reader import (
    normalize_for_alignment,
)


def make_block(
    text: str,
    *,
    page_index: int = 0,
    block_index: int = 0,
    x0: float = 72,
    y0: float = 72,
    x1: float = 300,
    y1: float | None = None,
    section_path: list[str] | None = None,
) -> TextBlock:
    resolved_y1 = y1 if y1 is not None else y0 + 18
    bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=resolved_y1)
    span = TextSpan(text=text, bbox=bbox, font="Helvetica", size=10, flags=0)
    line = TextLine(text=text, bbox=bbox, spans=[span], line_index=0)
    return TextBlock(
        text=text,
        normalized_text=normalize_for_alignment(text),
        page_index=page_index,
        block_index=block_index,
        bbox=bbox,
        lines=[line],
        block_type="paragraph",
        column_index=0,
        section_path=section_path or [],
    )


def test_insert_creates_added_change() -> None:
    matches = align_structured_blocks(
        [],
        [
            make_block(
                "The buyer shall provide quarterly reports.",
                section_path=["4. Reports"],
            )
        ],
    )

    changes = build_changes_from_alignment(matches)

    assert len(changes) == 1
    assert changes[0].change_id == "CHG-0001"
    assert changes[0].change_type == "added"
    assert changes[0].revised_text == "The buyer shall provide quarterly reports."
    assert changes[0].revised_location is not None
    assert changes[0].revised_location.block_index == 0
    assert changes[0].section_path == ["4. Reports"]


def test_delete_creates_deleted_change() -> None:
    matches = align_structured_blocks(
        [make_block("The seller may terminate on written notice.")],
        [],
    )

    changes = build_changes_from_alignment(matches)

    assert len(changes) == 1
    assert changes[0].change_type == "deleted"
    assert changes[0].original_location is not None
    assert changes[0].revised_location is None


def test_replace_creates_modified_change_with_changed_fragments() -> None:
    matches = align_structured_blocks(
        [make_block("Buyer shall pay the invoice within 30 days.")],
        [make_block("Buyer shall pay the invoice within 45 days.")],
    )

    changes = build_changes_from_alignment(matches)

    assert len(changes) == 1
    assert changes[0].change_type == "modified"
    assert changes[0].changed_fragments == ["45 days"]
    assert changes[0].confidence >= 0.75


def test_equal_creates_no_change() -> None:
    matches = align_structured_blocks(
        [make_block("Confidentiality survives termination.")],
        [make_block("Confidentiality survives termination.")],
    )

    assert build_changes_from_alignment(matches) == []


def test_uncertain_creates_uncertain_change() -> None:
    match = BlockMatch(
        original_block_id="page-0-block-0",
        revised_block_id="page-0-block-1",
        operation="uncertain",
        similarity=0.4,
        original_text="Payment shall be made within 30 days.",
        revised_text="This agreement is governed by Delaware law.",
        original_page_index=0,
        revised_page_index=0,
        section_path=["1. General"],
    )

    changes = build_changes_from_alignment([match])

    assert len(changes) == 1
    assert changes[0].change_type == "uncertain"
    assert changes[0].confidence == 0.4


def test_section_path_and_bbox_are_preserved() -> None:
    matches = align_structured_blocks(
        [
            make_block(
                "Buyer shall pay within 30 days.",
                section_path=["2. Payment Terms"],
                x0=72,
                y0=100,
                x1=300,
            )
        ],
        [
            make_block(
                "Buyer shall pay within 45 days.",
                section_path=["2. Payment Terms"],
                x0=72,
                y0=120,
                x1=300,
            )
        ],
    )

    changes = build_changes_from_alignment(matches)

    assert changes[0].section_path == ["2. Payment Terms"]
    assert changes[0].revised_location is not None
    assert changes[0].revised_location.bbox is not None
    assert changes[0].revised_location.bbox.y0 == 120
