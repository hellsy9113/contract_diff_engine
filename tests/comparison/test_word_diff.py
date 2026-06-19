from __future__ import annotations

from contract_diff.comparison.word_diff import (
    WordDiffOp,
    build_changes_from_word_diff,
    diff_word_streams,
)
from contract_diff.extraction.structured.models import (
    DocumentWordStream,
    PageInfo,
    WordToken,
)
from contract_diff.extraction.structured.word_tokens import normalize_word_token_text


def test_single_word_change_is_one_replace_operation() -> None:
    original = make_stream("The tenant shall pay rent monthly.")
    revised = make_stream("The tenant must pay rent monthly.")

    changes = _changed_ops(original, revised)

    assert len(changes) == 1
    assert changes[0].type == "replace"
    assert [token.text for token in changes[0].original_tokens] == ["shall"]
    assert [token.text for token in changes[0].revised_tokens] == ["must"]
    assert changes[0].original_start == 2
    assert changes[0].original_end == 3
    assert changes[0].revised_start == 2
    assert changes[0].revised_end == 3


def test_inserted_words_are_one_insert_operation() -> None:
    original = make_stream("The tenant shall pay rent monthly.")
    revised = make_stream("The tenant shall pay rent on time monthly.")

    changes = _changed_ops(original, revised)

    assert len(changes) == 1
    assert changes[0].type == "insert"
    assert changes[0].original_tokens == []
    assert [token.text for token in changes[0].revised_tokens] == ["on", "time"]


def test_deleted_word_is_one_delete_operation() -> None:
    original = make_stream("The tenant shall pay rent monthly.")
    revised = make_stream("The tenant shall pay monthly.")

    changes = _changed_ops(original, revised)

    assert len(changes) == 1
    assert changes[0].type == "delete"
    assert [token.text for token in changes[0].original_tokens] == ["rent"]
    assert changes[0].revised_tokens == []


def test_known_pki_pattern_creates_delete_change_with_after_anchor() -> None:
    original = make_stream("[28]. Public Key Infrastructure (PKI), the trust framework")
    revised = make_stream("[28]. (PKI), the trust framework")

    ops = _changed_ops(original, revised)
    changes = build_changes_from_word_diff(original, revised)

    assert len(ops) == 1
    assert ops[0].type == "delete"
    assert [token.text for token in ops[0].original_tokens] == [
        "Public",
        "Key",
        "Infrastructure",
    ]
    assert ops[0].revised_tokens == []

    assert len(changes) == 1
    assert changes[0].change_id == "CHG-0001"
    assert changes[0].change_type == "deleted"
    assert changes[0].original_text == "Public Key Infrastructure"
    assert changes[0].revised_text is None
    assert changes[0].changed_fragments == []
    assert changes[0].revised_location is not None
    assert changes[0].revised_location.page_index == 0
    assert changes[0].metadata["delete_anchor_strategy"] == (
        "nearest_surviving_revised_token_after"
    )
    assert changes[0].metadata["delete_anchor_token_id"] == "token-1"
    assert changes[0].metadata["annotation_context"] == {
        "before_word": "[28].",
        "deleted_text": "Public Key Infrastructure",
        "inserted_text": None,
        "after_word": "(PKI),",
        "display_markdown": "[28]. ~~Public Key Infrastructure~~ (PKI),",
        "plain_text": "[28]. Public Key Infrastructure (PKI),",
    }


def test_delete_without_revised_tokens_falls_back_to_original_location() -> None:
    original = make_stream("Public Key Infrastructure")
    revised = make_stream("")

    changes = build_changes_from_word_diff(original, revised)

    assert len(changes) == 1
    assert changes[0].change_type == "deleted"
    assert changes[0].revised_location == changes[0].original_location
    assert changes[0].metadata["delete_anchor_strategy"] == (
        "original_location_fallback"
    )


def test_paragraph_sized_content_with_one_word_change_stays_word_level() -> None:
    original = make_stream(
        "The tenant shall maintain insurance coverage throughout the term and "
        "shall promptly notify the landlord of any cancellation renewal dispute "
        "claim default notice assignment transfer or material adverse event."
    )
    revised = make_stream(
        "The tenant shall maintain insurance coverage throughout the term and "
        "shall promptly notify the landlord of any cancellation renewal dispute "
        "claim default notice assignment transfer or material adverse breach."
    )

    changes = _changed_ops(original, revised)

    assert len(changes) == 1
    assert changes[0].type == "replace"
    assert [token.text for token in changes[0].original_tokens] == ["event."]
    assert [token.text for token in changes[0].revised_tokens] == ["breach."]


def test_changes_preserve_ranges_and_renderer_change_metadata() -> None:
    original = make_stream("The tenant shall pay rent monthly.")
    revised = make_stream("The tenant must pay rent monthly.")

    changes = build_changes_from_word_diff(original, revised)

    assert len(changes) == 1
    assert changes[0].change_type == "modified"
    assert changes[0].original_text == "shall"
    assert changes[0].revised_text == "must"
    assert changes[0].changed_fragments == ["must"]
    assert changes[0].metadata["comparison_strategy"] == "document_word_diff"
    assert changes[0].metadata["original_start"] == 2
    assert changes[0].metadata["revised_start"] == 2
    assert changes[0].metadata["annotation_context"] == {
        "before_word": "tenant",
        "deleted_text": "shall",
        "inserted_text": "must",
        "after_word": "pay",
        "display_markdown": "tenant ~~shall~~ must pay",
        "plain_text": "tenant shall must pay",
    }


def _changed_ops(
    original: DocumentWordStream,
    revised: DocumentWordStream,
) -> list[WordDiffOp]:
    return [op for op in diff_word_streams(original, revised) if op.type != "equal"]


def make_stream(text: str) -> DocumentWordStream:
    words = text.split()
    tokens = [
        WordToken(
            id=f"token-{index}",
            text=word,
            normalized=normalize_word_token_text(word),
            page_number=1,
            bbox=(72 + index * 20, 72, 88 + index * 20, 84),
            line_id="page-0-block-0-line-0",
            block_id="page-0-block-0",
            paragraph_id="page-0-block-0",
            section_heading="Payment",
            token_index=index,
        )
        for index, word in enumerate(words)
    ]
    return DocumentWordStream(
        tokens=tokens,
        pages=[
            PageInfo(
                page_number=1,
                page_index=0,
                width=500,
                height=700,
                token_start_index=0 if tokens else None,
                token_end_index=len(tokens) if tokens else None,
            )
        ],
        source_file_name=None,
    )
