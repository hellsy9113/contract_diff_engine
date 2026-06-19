from __future__ import annotations

from contract_diff.comparison.annotation_context import build_annotation_context
from contract_diff.comparison.word_diff import WordDiffOp, diff_word_streams
from contract_diff.extraction.structured.models import (
    DocumentWordStream,
    PageInfo,
    WordToken,
)
from contract_diff.extraction.structured.word_tokens import normalize_word_token_text


def test_delete_context_strikes_deleted_text_only() -> None:
    original = make_stream(
        "algorithm [1]. Apart from Shor’s algorithm, Grover’s algorithm also "
        "poses a significant challenge to modern cryptography. It offers"
    )
    revised = make_stream("algorithm [1]. It offers")
    op = _changed_op(original, revised)

    context = build_annotation_context(op, original, revised)

    assert context.before_word == "[1]."
    assert context.deleted_text == (
        "Apart from Shor’s algorithm, Grover’s algorithm also poses a "
        "significant challenge to modern cryptography."
    )
    assert context.inserted_text is None
    assert context.after_word == "It"
    assert context.display_markdown == (
        "[1]. ~~Apart from Shor’s algorithm, Grover’s algorithm also poses a "
        "significant challenge to modern cryptography.~~ It"
    )


def test_replace_context_keeps_one_before_and_after_word() -> None:
    original = make_stream("provide advanced properties like unlinkability")
    revised = make_stream("provide advanced security features such as unlinkability")
    op = _changed_op(original, revised)

    context = build_annotation_context(op, original, revised)

    assert context.before_word == "provide"
    assert context.deleted_text == "advanced properties like"
    assert context.inserted_text == "advanced security features such as"
    assert context.after_word == "unlinkability"
    assert context.display_markdown == (
        "provide ~~advanced properties like~~ advanced security features such "
        "as unlinkability"
    )


def test_insert_context_marks_inserted_text_only() -> None:
    original = make_stream("security [3], [14]. transition")
    revised = make_stream(
        "security [3], [14]. Ultimately, this research supports... transition"
    )
    op = _changed_op(original, revised)

    context = build_annotation_context(op, original, revised)

    assert context.before_word == "[14]."
    assert context.deleted_text is None
    assert context.inserted_text == "Ultimately, this research supports..."
    assert context.after_word == "transition"
    assert context.display_markdown == (
        "[14]. ++Ultimately, this research supports...++ transition"
    )


def test_start_of_document_change_has_no_before_word() -> None:
    original = make_stream("tenant pays rent")
    revised = make_stream("The tenant pays rent")
    op = _changed_op(original, revised)

    context = build_annotation_context(op, original, revised)

    assert context.before_word is None
    assert context.inserted_text == "The"
    assert context.after_word == "tenant"
    assert context.display_markdown == "++The++ tenant"


def test_end_of_document_change_has_no_after_word() -> None:
    original = make_stream("tenant pays rent")
    revised = make_stream("tenant pays rent monthly.")
    op = _changed_op(original, revised)

    context = build_annotation_context(op, original, revised)

    assert context.before_word == "rent"
    assert context.inserted_text == "monthly."
    assert context.after_word is None
    assert context.display_markdown == "rent ++monthly.++"


def _changed_op(
    original: DocumentWordStream,
    revised: DocumentWordStream,
) -> WordDiffOp:
    changes = [op for op in diff_word_streams(original, revised) if op.type != "equal"]
    assert len(changes) == 1
    return changes[0]


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
            section_heading=None,
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
