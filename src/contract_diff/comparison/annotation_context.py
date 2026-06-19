from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from contract_diff.extraction.structured.models import DocumentWordStream, WordToken

if TYPE_CHECKING:
    from contract_diff.comparison.word_diff import WordDiffOp

MAX_CHANGED_TEXT_CHARS = 500
_TRUNCATION_MARKER = " ... "


class AnnotationContext(BaseModel):
    """Short display context for a word-level annotation."""

    model_config = ConfigDict(frozen=True)

    before_word: str | None
    deleted_text: str | None
    inserted_text: str | None
    after_word: str | None
    display_markdown: str
    plain_text: str


def build_annotation_context(
    op: WordDiffOp,
    original_stream: DocumentWordStream,
    revised_stream: DocumentWordStream,
) -> AnnotationContext:
    """Build one-word annotation context from structured token metadata."""

    ranges = _context_ranges(op, original_stream, revised_stream)
    before_word = _before_word(
        original_stream,
        revised_stream,
        ranges.original_start,
        ranges.revised_start,
    )
    after_word = _after_word(
        original_stream,
        revised_stream,
        ranges.original_end,
        ranges.revised_end,
    )
    deleted_text = _changed_text(ranges.original_tokens)
    inserted_text = _changed_text(ranges.revised_tokens)
    display_markdown = _display_markdown(
        operation=op.type,
        before_word=before_word,
        deleted_text=deleted_text,
        inserted_text=inserted_text,
        after_word=after_word,
    )
    plain_text = _plain_text(
        before_word=before_word,
        deleted_text=deleted_text,
        inserted_text=inserted_text,
        after_word=after_word,
    )

    return AnnotationContext(
        before_word=before_word,
        deleted_text=deleted_text or None,
        inserted_text=inserted_text or None,
        after_word=after_word,
        display_markdown=display_markdown,
        plain_text=plain_text,
    )


class _ContextRanges(BaseModel):
    model_config = ConfigDict(frozen=True)

    original_start: int
    original_end: int
    revised_start: int
    revised_end: int
    original_tokens: list[WordToken]
    revised_tokens: list[WordToken]


def _context_ranges(
    op: WordDiffOp,
    original_stream: DocumentWordStream,
    revised_stream: DocumentWordStream,
) -> _ContextRanges:
    original_start = op.original_start
    revised_start = op.revised_start
    original_tokens = list(op.original_tokens)
    revised_tokens = list(op.revised_tokens)

    if _should_absorb_shared_left_context(op, original_stream, revised_stream):
        original_start -= 1
        revised_start -= 1
        original_tokens.insert(0, original_stream.tokens[original_start])
        revised_tokens.insert(0, revised_stream.tokens[revised_start])

    return _ContextRanges(
        original_start=original_start,
        original_end=op.original_end,
        revised_start=revised_start,
        revised_end=op.revised_end,
        original_tokens=original_tokens,
        revised_tokens=revised_tokens,
    )


def _should_absorb_shared_left_context(
    op: WordDiffOp,
    original_stream: DocumentWordStream,
    revised_stream: DocumentWordStream,
) -> bool:
    if op.type != "replace":
        return False

    if len(op.original_tokens) < 2 and len(op.revised_tokens) < 2:
        return False

    if op.original_start < 2 or op.revised_start < 2:
        return False

    original_previous = original_stream.tokens[op.original_start - 1]
    revised_previous = revised_stream.tokens[op.revised_start - 1]
    return original_previous.normalized == revised_previous.normalized


def _before_word(
    original_stream: DocumentWordStream,
    revised_stream: DocumentWordStream,
    original_start: int,
    revised_start: int,
) -> str | None:
    original_token = _token_at(original_stream, original_start - 1)
    revised_token = _token_at(revised_stream, revised_start - 1)

    if not _matching_equal_tokens(original_token, revised_token):
        return None

    assert revised_token is not None
    return revised_token.text


def _after_word(
    original_stream: DocumentWordStream,
    revised_stream: DocumentWordStream,
    original_end: int,
    revised_end: int,
) -> str | None:
    original_token = _token_at(original_stream, original_end)
    revised_token = _token_at(revised_stream, revised_end)

    if not _matching_equal_tokens(original_token, revised_token):
        return None

    assert revised_token is not None
    return revised_token.text


def _token_at(stream: DocumentWordStream, index: int) -> WordToken | None:
    if index < 0 or index >= len(stream.tokens):
        return None

    return stream.tokens[index]


def _matching_equal_tokens(
    original_token: WordToken | None,
    revised_token: WordToken | None,
) -> bool:
    if original_token is None or revised_token is None:
        return False

    return original_token.normalized == revised_token.normalized


def _changed_text(tokens: list[WordToken]) -> str:
    return _truncate_middle(" ".join(token.text for token in tokens).strip())


def _display_markdown(
    *,
    operation: str,
    before_word: str | None,
    deleted_text: str,
    inserted_text: str,
    after_word: str | None,
) -> str:
    parts: list[str] = []

    if before_word:
        parts.append(before_word)

    if operation == "insert":
        if inserted_text:
            parts.append(f"++{inserted_text}++")
    elif operation == "delete":
        if deleted_text:
            parts.append(f"~~{deleted_text}~~")
    else:
        if deleted_text:
            parts.append(f"~~{deleted_text}~~")

        if inserted_text:
            parts.append(inserted_text)

    if after_word:
        parts.append(after_word)

    return " ".join(parts).strip()


def _plain_text(
    *,
    before_word: str | None,
    deleted_text: str,
    inserted_text: str,
    after_word: str | None,
) -> str:
    parts = [
        part for part in (before_word, deleted_text, inserted_text, after_word) if part
    ]
    return " ".join(parts).strip()


def _truncate_middle(text: str) -> str:
    if len(text) <= MAX_CHANGED_TEXT_CHARS:
        return text

    available = MAX_CHANGED_TEXT_CHARS - len(_TRUNCATION_MARKER)
    head_length = available // 2
    tail_length = available - head_length
    return f"{text[:head_length]}{_TRUNCATION_MARKER}{text[-tail_length:]}"
