from __future__ import annotations

from contract_diff.comparison.token_diff import (
    diff_modified_text,
    get_revised_changed_fragments,
    tokenize_for_diff,
)


def test_tokenize_for_diff_splits_words_numbers_and_punctuation() -> None:
    tokens = tokenize_for_diff("Payment: $1,000 within 30 days.")

    assert tokens == ["Payment", ":", "$1,000", "within", "30", "days", "."]


def test_number_change_returns_number_phrase() -> None:
    fragments = get_revised_changed_fragments(
        "Buyer shall pay within 30 days.",
        "Buyer shall pay within 45 days.",
    )

    assert fragments == ["45 days"]


def test_added_phrase_inside_sentence_returns_only_added_phrase() -> None:
    fragments = get_revised_changed_fragments(
        "The buyer shall provide reports.",
        "The buyer shall provide quarterly audit reports.",
    )

    assert fragments == ["quarterly audit"]


def test_modified_legal_sentence_does_not_return_entire_sentence() -> None:
    original = "The recipient shall protect confidential information."
    revised = (
        "The recipient shall protect confidential information using "
        "commercially reasonable safeguards."
    )

    fragments = get_revised_changed_fragments(original, revised)

    assert "commercially reasonable safeguards" in fragments
    assert revised not in fragments


def test_whitespace_only_change_returns_no_fragments() -> None:
    fragments = get_revised_changed_fragments(
        "Buyer shall pay within 30 days.",
        "Buyer   shall\npay within 30 days.",
    )

    assert fragments == []


def test_smart_quote_only_change_returns_no_fragments() -> None:
    fragments = get_revised_changed_fragments(
        '"Confidential Information" means data.',
        "“Confidential Information” means data.",
    )

    assert fragments == []


def test_punctuation_only_change_is_ignored() -> None:
    changes = diff_modified_text(
        "Buyer shall pay within 30 days.",
        "Buyer shall pay within 30 days!",
    )

    assert changes == []


def test_long_paragraph_insertion_returns_phrase_not_full_paragraph() -> None:
    original = "The buyer shall maintain records."
    revised = (
        "The buyer shall maintain records. The seller shall also provide "
        "quarterly security reports and cooperate with audits upon request."
    )

    fragments = get_revised_changed_fragments(original, revised)

    assert fragments
    assert all(fragment != revised for fragment in fragments)
    assert all(len(fragment.split()) <= 8 for fragment in fragments)
