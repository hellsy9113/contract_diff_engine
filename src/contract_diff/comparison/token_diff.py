from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Literal

from pydantic import BaseModel, ConfigDict

from contract_diff.comparison.utils.text_diff_helpers import normalize_for_alignment

TokenOperation = Literal["equal", "insert", "delete", "replace"]

COMMON_STANDALONE_WORDS = frozenset(
    {
        "the",
        "and",
        "of",
        "in",
        "to",
        "for",
        "with",
        "this",
        "that",
        "using",
        "a",
        "an",
    }
)
MIN_PHRASE_WORDS = 3
MAX_PHRASE_WORDS = 8

_TOKEN_RE = re.compile(
    r"""
    \$?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?
    |\d+(?:\.\d+)?%?
    |\d{1,2}[/-]\d{1,2}[/-]\d{2,4}
    |[A-Za-z]+(?:['’][A-Za-z]+)?
    |[^\w\s]
    """,
    re.VERBOSE,
)
_WORD_RE = re.compile(r"[A-Za-z0-9$%]+(?:['’][A-Za-z0-9]+)?")
_NO_SPACE_BEFORE = frozenset({".", ",", ";", ":", "!", "?", ")", "]", "}"})
_NO_SPACE_AFTER = frozenset({"(", "[", "{", "$"})
_UNIT_WORDS = frozenset(
    {
        "day",
        "days",
        "month",
        "months",
        "year",
        "years",
        "percent",
        "percentage",
        "dollar",
        "dollars",
        "usd",
        "eur",
        "gbp",
    }
)


class TokenChange(BaseModel):
    """One token-level difference inside a modified text block."""

    model_config = ConfigDict(frozen=True)

    operation: TokenOperation
    original_text: str | None
    revised_text: str | None
    changed_fragment: str | None


def tokenize_for_diff(text: str) -> list[str]:
    """Split text into stable word, number, currency, date, and punctuation tokens."""

    return _TOKEN_RE.findall(text)


def diff_modified_text(original_text: str, revised_text: str) -> list[TokenChange]:
    """Return token-level changes while ignoring normalization-only differences."""

    if normalize_for_alignment(original_text) == normalize_for_alignment(revised_text):
        return []

    original_tokens = tokenize_for_diff(original_text)
    revised_tokens = tokenize_for_diff(revised_text)
    original_keys = [_token_key(token) for token in original_tokens]
    revised_keys = [_token_key(token) for token in revised_tokens]
    matcher = SequenceMatcher(None, original_keys, revised_keys)
    changes: list[TokenChange] = []

    for (
        tag,
        original_start,
        original_end,
        revised_start,
        revised_end,
    ) in matcher.get_opcodes():
        original_fragment = _join_tokens(original_tokens[original_start:original_end])
        revised_fragment = _join_tokens(revised_tokens[revised_start:revised_end])

        if tag == "equal":
            continue

        if tag == "delete":
            if _is_punctuation_only(original_fragment):
                continue

            changes.append(
                TokenChange(
                    operation="delete",
                    original_text=original_fragment,
                    revised_text=None,
                    changed_fragment=None,
                )
            )
            continue

        if tag == "insert":
            changed_fragment = _clean_fragment(revised_fragment)

            if not _is_renderable_changed_fragment(changed_fragment):
                continue

            changes.append(
                TokenChange(
                    operation="insert",
                    original_text=None,
                    revised_text=revised_fragment,
                    changed_fragment=changed_fragment,
                )
            )
            continue

        changed_fragment = _clean_fragment(revised_fragment)

        if not _is_renderable_changed_fragment(changed_fragment):
            continue

        changes.append(
            TokenChange(
                operation="replace",
                original_text=original_fragment,
                revised_text=revised_fragment,
                changed_fragment=changed_fragment,
            )
        )

    return changes


def get_revised_changed_fragments(
    original_text: str,
    revised_text: str,
) -> list[str]:
    """Return revised-side fragments that are suitable search targets for rendering."""

    if normalize_for_alignment(original_text) == normalize_for_alignment(revised_text):
        return []

    original_tokens = tokenize_for_diff(original_text)
    revised_tokens = tokenize_for_diff(revised_text)
    original_keys = [_token_key(token) for token in original_tokens]
    revised_keys = [_token_key(token) for token in revised_tokens]
    matcher = SequenceMatcher(None, original_keys, revised_keys)
    fragments: list[str] = []

    for (
        tag,
        _original_start,
        _original_end,
        revised_start,
        revised_end,
    ) in matcher.get_opcodes():
        if tag in {"equal", "delete"}:
            continue

        expanded_tokens = _expand_changed_tokens(
            revised_tokens,
            revised_start,
            revised_end,
        )
        fragment = _clean_fragment(_join_tokens(expanded_tokens))
        fragments.extend(_searchable_fragments(fragment))

    return _unique(fragments)


def _expand_changed_tokens(
    tokens: list[str],
    start: int,
    end: int,
) -> list[str]:
    fragment_tokens = tokens[start:end]

    if not fragment_tokens:
        return []

    fragment_words = _words(fragment_tokens)

    if len(fragment_words) == 1 and _is_number_like(fragment_words[0]):
        if end < len(tokens) and _token_key(tokens[end]) in _UNIT_WORDS:
            return tokens[start : end + 1]

        if start > 0 and _token_key(tokens[start - 1]) in _UNIT_WORDS:
            return tokens[start - 1 : end]

    return fragment_tokens


def _searchable_fragments(text: str) -> list[str]:
    words = _WORD_RE.findall(text)
    trimmed_words = _trim_common_edges(words)

    if not trimmed_words:
        return []

    if len(trimmed_words) == 1:
        word = trimmed_words[0]
        return [word] if _is_searchable_single_word(word) else []

    if len(trimmed_words) <= MAX_PHRASE_WORDS:
        phrase = " ".join(trimmed_words)
        return [phrase] if _is_searchable_phrase(phrase) else []

    fragments: list[str] = []

    for window_size in range(MAX_PHRASE_WORDS, MIN_PHRASE_WORDS - 1, -1):
        for start in range(0, len(trimmed_words) - window_size + 1):
            phrase = " ".join(trimmed_words[start : start + window_size])

            if _is_searchable_phrase(phrase):
                fragments.append(phrase)

        if fragments:
            break

    return fragments


def _join_tokens(tokens: list[str]) -> str:
    text = ""

    for token in tokens:
        if not text:
            text = token
            continue

        if token in _NO_SPACE_BEFORE or text[-1] in _NO_SPACE_AFTER:
            text += token
        else:
            text += f" {token}"

    return text


def _token_key(token: str) -> str:
    return normalize_for_alignment(token)


def _clean_fragment(fragment: str) -> str:
    return fragment.strip().lstrip(".,;:!? ").strip()


def _words(tokens: list[str]) -> list[str]:
    return [word for token in tokens for word in _WORD_RE.findall(token)]


def _trim_common_edges(words: list[str]) -> list[str]:
    trimmed = list(words)

    while trimmed and _is_common_word(trimmed[0]):
        trimmed.pop(0)

    while trimmed and _is_common_word(trimmed[-1]):
        trimmed.pop()

    return trimmed


def _is_renderable_changed_fragment(fragment: str) -> bool:
    if not fragment:
        return False

    if _is_punctuation_only(fragment):
        return False

    return bool(_searchable_fragments(fragment))


def _is_searchable_phrase(phrase: str) -> bool:
    words = _WORD_RE.findall(phrase)

    if not words:
        return False

    if len(words) == 1:
        return _is_searchable_single_word(words[0])

    return any(not _is_common_word(word) for word in words)


def _is_searchable_single_word(word: str) -> bool:
    normalized = _token_key(word)

    if _is_number_like(word):
        return True

    return len(normalized) >= 3 and normalized not in COMMON_STANDALONE_WORDS


def _is_number_like(text: str) -> bool:
    return bool(re.search(r"\d", text))


def _is_common_word(word: str) -> bool:
    return _token_key(word) in COMMON_STANDALONE_WORDS


def _is_punctuation_only(text: str) -> bool:
    return bool(text) and all(not character.isalnum() for character in text)


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_items: list[str] = []

    for item in items:
        key = _token_key(item)

        if key in seen:
            continue

        seen.add(key)
        unique_items.append(item)

    return unique_items
