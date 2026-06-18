from __future__ import annotations

from contract_diff.extraction.structured.columns import (
    apply_column_detection,
    detect_columns_for_page,
)
from contract_diff.extraction.structured.models import TextBlock
from tests.extraction.structured.helpers import make_block, make_document, make_page


def test_single_column_page_assigns_column_zero() -> None:
    blocks = [
        make_block("First paragraph.", block_index=0, x0=72, x1=300, y0=100),
        make_block("Second paragraph.", block_index=1, x0=75, x1=310, y0=140),
        make_block("Third paragraph.", block_index=2, x0=70, x1=305, y0=180),
        make_block("Fourth paragraph.", block_index=3, x0=76, x1=312, y0=220),
    ]

    assert detect_columns_for_page(blocks, page_width=500) == {
        0: 0,
        1: 0,
        2: 0,
        3: 0,
    }


def test_two_column_page_assigns_left_and_right_columns() -> None:
    blocks = _two_column_blocks()

    assert detect_columns_for_page(blocks, page_width=500) == {
        0: 0,
        1: 1,
        2: 0,
        3: 1,
    }


def test_two_column_reading_order_is_left_column_then_right_column() -> None:
    document = make_document([make_page(_two_column_blocks())])

    ordered = apply_column_detection(document)

    assert [block.text for block in ordered.pages[0].blocks] == [
        "Left 1",
        "Left 2",
        "Right 1",
        "Right 2",
    ]


def test_header_footer_blocks_are_ignored_for_column_detection() -> None:
    blocks = [
        make_block("Header", block_index=0, x0=10, x1=490, y0=20, block_type="header"),
        make_block("Left 1", block_index=1, x0=72, x1=180, y0=100),
        make_block("Right 1", block_index=2, x0=300, x1=430, y0=100),
        make_block("Left 2", block_index=3, x0=72, x1=180, y0=140),
        make_block("Right 2", block_index=4, x0=300, x1=430, y0=140),
        make_block("Footer", block_index=5, x0=10, x1=490, y0=650, block_type="footer"),
    ]

    document = make_document([make_page(blocks)])
    ordered = apply_column_detection(document)

    assert ordered.pages[0].blocks[0].block_type == "header"
    assert ordered.pages[0].blocks[-1].block_type == "footer"
    assert ordered.pages[0].blocks[1].column_index == 0
    assert ordered.pages[0].blocks[3].column_index == 1


def _two_column_blocks() -> list[TextBlock]:
    return [
        make_block("Left 1", block_index=0, x0=72, x1=180, y0=100),
        make_block("Right 1", block_index=1, x0=300, x1=430, y0=100),
        make_block("Left 2", block_index=2, x0=72, x1=180, y0=140),
        make_block("Right 2", block_index=3, x0=300, x1=430, y0=140),
    ]
