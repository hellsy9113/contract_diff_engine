from __future__ import annotations

from contract_diff.alignment.structured_alignment import align_structured_blocks
from tests.extraction.structured.helpers import make_block


def test_identical_blocks_align_as_equal() -> None:
    original = [make_block("Payment shall be made within 30 days.")]
    revised = [make_block("Payment shall be made within 30 days.")]

    matches = align_structured_blocks(original, revised)

    assert [match.operation for match in matches] == ["equal"]
    assert matches[0].similarity == 1.0
    assert matches[0].original_block_id == "page-0-block-0"
    assert matches[0].revised_block_id == "page-0-block-0"


def test_inserted_block_aligns_as_insert() -> None:
    original = [make_block("Payment shall be made within 30 days.")]
    revised = [
        make_block("Payment shall be made within 30 days.", block_index=0),
        make_block("The buyer must provide quarterly reports.", block_index=1),
    ]

    matches = align_structured_blocks(original, revised)

    assert [match.operation for match in matches] == ["equal", "insert"]
    assert matches[1].original_block_id is None
    assert matches[1].revised_text == "The buyer must provide quarterly reports."


def test_deleted_block_aligns_as_delete() -> None:
    original = [
        make_block("Payment shall be made within 30 days.", block_index=0),
        make_block("The buyer must provide quarterly reports.", block_index=1),
    ]
    revised = [make_block("Payment shall be made within 30 days.")]

    matches = align_structured_blocks(original, revised)

    assert [match.operation for match in matches] == ["equal", "delete"]
    assert matches[1].original_text == "The buyer must provide quarterly reports."
    assert matches[1].revised_block_id is None


def test_similar_modified_block_aligns_as_replace() -> None:
    original = [make_block("Buyer shall pay the invoice within 30 days.")]
    revised = [make_block("Buyer shall pay the invoice within 45 days.")]

    matches = align_structured_blocks(original, revised)

    assert [match.operation for match in matches] == ["replace"]
    assert matches[0].similarity >= 0.75
    assert matches[0].original_text == "Buyer shall pay the invoice within 30 days."
    assert matches[0].revised_text == "Buyer shall pay the invoice within 45 days."


def test_unrelated_replace_splits_into_delete_and_insert() -> None:
    original = [make_block("Payment shall be made within 30 days.")]
    revised = [make_block("This agreement is governed by Delaware law.")]

    matches = align_structured_blocks(original, revised)

    assert [match.operation for match in matches] == ["delete", "insert"]
    assert matches[0].original_text == "Payment shall be made within 30 days."
    assert matches[1].revised_text == "This agreement is governed by Delaware law."


def test_page_shift_does_not_create_false_change() -> None:
    original = [make_block("Confidentiality survives termination.", page_index=0)]
    revised = [make_block("Confidentiality survives termination.", page_index=3)]

    matches = align_structured_blocks(original, revised)

    assert [match.operation for match in matches] == ["equal"]
    assert matches[0].original_page_index == 0
    assert matches[0].revised_page_index == 3


def test_whitespace_only_difference_is_ignored() -> None:
    original = [make_block("Buyer shall pay within 30 days.")]
    revised = [make_block("Buyer   shall\npay within   30 days.")]

    matches = align_structured_blocks(original, revised)

    assert [match.operation for match in matches] == ["equal"]
    assert matches[0].similarity == 1.0


def test_section_metadata_is_preserved() -> None:
    original = [
        make_block(
            "Buyer shall pay within 30 days.",
            section_path=["2. Payment Terms"],
        )
    ]
    revised = [
        make_block(
            "Buyer shall pay within 45 days.",
            section_path=["2. Payment Terms"],
        )
    ]

    matches = align_structured_blocks(original, revised)

    assert [match.operation for match in matches] == ["replace"]
    assert matches[0].section_path == ["2. Payment Terms"]
