from __future__ import annotations

from contract_diff.extraction.structured.block_classifier import (
    classify_block,
    classify_blocks,
)
from tests.extraction.structured.helpers import make_block, make_document, make_page


def test_numbered_heading_is_detected() -> None:
    assert classify_block(make_block("1. Introduction")) == "heading"
    assert classify_block(make_block("2.1 Confidentiality")) == "heading"
    assert classify_block(make_block("Section 5.2 Payment Terms")) == "heading"


def test_article_schedule_and_exhibit_headings_are_detected() -> None:
    assert classify_block(make_block("ARTICLE IV")) == "heading"
    assert classify_block(make_block("EXHIBIT A")) == "heading"
    assert classify_block(make_block("SCHEDULE 1")) == "heading"


def test_all_caps_short_heading_is_detected() -> None:
    assert classify_block(make_block("CONFIDENTIALITY")) == "heading"


def test_list_item_is_detected() -> None:
    assert classify_block(make_block("(a) The supplier shall deliver goods.")) == (
        "list_item"
    )
    assert classify_block(make_block("(ii) The buyer may inspect goods.")) == (
        "list_item"
    )
    assert classify_block(make_block("• The recipient shall keep records.")) == (
        "list_item"
    )


def test_paragraph_is_detected() -> None:
    assert classify_block(
        make_block(
            "The receiving party shall protect confidential information using "
            "commercially reasonable safeguards."
        )
    ) == "paragraph"


def test_noise_is_detected() -> None:
    assert classify_block(make_block("")) == "noise"
    assert classify_block(make_block("14")) == "noise"
    assert classify_block(make_block("---")) == "noise"


def test_header_footer_classification_is_preserved() -> None:
    assert classify_block(make_block("Agreement", block_type="header")) == "header"
    assert classify_block(make_block("Confidential", block_type="footer")) == "footer"


def test_table_candidate_basic_heuristic() -> None:
    assert classify_block(make_block("Fee    Term    Cap\n100    30    500")) == (
        "table_candidate"
    )


def test_classify_blocks_returns_updated_document() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block("1. Payment Terms", block_index=0),
                    make_block(
                        "The buyer shall pay the purchase price within thirty days.",
                        block_index=1,
                    ),
                ]
            )
        ]
    )

    classified = classify_blocks(document)

    assert [block.block_type for block in classified.pages[0].blocks] == [
        "heading",
        "paragraph",
    ]
