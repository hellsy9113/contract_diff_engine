from __future__ import annotations

from contract_diff.extraction.structured.header_footer import is_page_number_text
from contract_diff.extraction.structured.reading_order import (
    get_comparison_blocks,
    resolve_reading_order,
)
from tests.extraction.structured.helpers import make_block, make_document, make_page


def test_repeated_header_is_classified_and_preserved() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block("Master Services Agreement", page_index=0, y0=20, y1=35),
                    make_block("First body paragraph.", page_index=0, y0=120, y1=140),
                ],
                page_index=0,
            ),
            make_page(
                [
                    make_block("Master Services Agreement", page_index=1, y0=20, y1=35),
                    make_block("Second body paragraph.", page_index=1, y0=120, y1=140),
                ],
                page_index=1,
            ),
        ]
    )

    ordered = resolve_reading_order(document)

    assert ordered.pages[0].blocks[0].block_type == "header"
    assert ordered.pages[1].blocks[0].block_type == "header"
    assert ordered.pages[0].blocks[0].text == "Master Services Agreement"


def test_repeated_footer_is_classified_and_preserved() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block("First body paragraph.", page_index=0, y0=120, y1=140),
                    make_block("Confidential", page_index=0, y0=635, y1=660),
                ],
                page_index=0,
            ),
            make_page(
                [
                    make_block("Second body paragraph.", page_index=1, y0=120, y1=140),
                    make_block("Confidential", page_index=1, y0=635, y1=660),
                ],
                page_index=1,
            ),
        ]
    )

    ordered = resolve_reading_order(document)

    assert ordered.pages[0].blocks[-1].block_type == "footer"
    assert ordered.pages[1].blocks[-1].block_type == "footer"


def test_page_numbers_are_detected_as_footer_noise() -> None:
    assert is_page_number_text("1")
    assert is_page_number_text("Page 12")
    assert is_page_number_text("- 7 -")
    assert is_page_number_text("3 of 10")

    document = make_document(
        [
            make_page(
                [
                    make_block("Body paragraph.", y0=120, y1=140),
                    make_block("Page 1", y0=640, y1=655),
                ]
            )
        ]
    )

    ordered = resolve_reading_order(document)

    assert ordered.pages[0].blocks[-1].block_type == "footer"


def test_comparison_blocks_exclude_headers_and_footers() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block("Shared Header", page_index=0, y0=20, y1=35),
                    make_block("Body one.", page_index=0, y0=120, y1=140),
                    make_block("1", page_index=0, y0=640, y1=655),
                ],
                page_index=0,
            ),
            make_page(
                [
                    make_block("Shared Header", page_index=1, y0=20, y1=35),
                    make_block("Body two.", page_index=1, y0=120, y1=140),
                    make_block("2", page_index=1, y0=640, y1=655),
                ],
                page_index=1,
            ),
        ]
    )

    ordered = resolve_reading_order(document)
    comparison_texts = [block.text for block in get_comparison_blocks(ordered)]

    assert comparison_texts == ["Body one.", "Body two."]


def test_single_column_reading_order_sorts_top_to_bottom_then_left_to_right() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block("Second", x0=200, y0=120, y1=140),
                    make_block("First", x0=72, y0=120, y1=140),
                    make_block("Third", x0=72, y0=180, y1=200),
                ]
            )
        ]
    )

    ordered = resolve_reading_order(document)

    assert [block.text for block in ordered.pages[0].blocks] == [
        "First",
        "Second",
        "Third",
    ]
