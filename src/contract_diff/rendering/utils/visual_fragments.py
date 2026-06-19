from __future__ import annotations

import re

from contract_diff.comparison.utils.text_diff_helpers import normalize_for_alignment
from contract_diff.rendering.styles.pdf_colors import MIN_FRAGMENT_LENGTH

COMMON_VISUAL_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
    }
)
MAX_VISUAL_FRAGMENT_LENGTH = 96
MIN_PHRASE_WORDS = 3
MAX_PHRASE_WORDS = 8

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?")
_PUNCTUATION_RE = re.compile(r"^[^\w]+$")


def prepare_visual_fragments(text: str) -> list[str]:
    """
    Convert raw changed text into safe visual fragments.

    Rendering prefers complete, searchable phrases over full paragraphs or tiny
    tokens. The original text is still used for PDF search; normalization here
    only removes visual noise from candidate fragments.
    """

    cleaned = _clean_visual_text(text)
    words = _WORD_RE.findall(cleaned)
    words = _trim_common_edge_words(words)

    if len(words) == 1:
        return [words[0]] if _is_meaningful_word(words[0]) else []

    if not words:
        return []

    if len(words) <= 4:
        phrase = " ".join(words)
        return [phrase] if _is_meaningful_fragment(phrase) else []

    fragments: list[str] = []

    for window_size in range(4, MIN_PHRASE_WORDS - 1, -1):
        for start in range(0, len(words) - window_size + 1):
            phrase = " ".join(words[start : start + window_size])

            if _is_meaningful_fragment(phrase):
                fragments.append(phrase)

        if fragments:
            break

    if fragments:
        return _unique(fragments)

    return [cleaned] if _is_meaningful_fragment(cleaned) else []


def _clean_visual_text(text: str) -> str:
    normalized = text.replace("\u00ad", "")
    normalized = normalized.replace("￾", "-")
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.replace("‘", "'").replace("’", "'")
    normalized = normalized.replace("‐", "-").replace("‑", "-")
    normalized = normalized.replace("–", "-").replace("—", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().strip(".,;:!? ")


def _is_meaningful_fragment(fragment: str) -> bool:
    if _PUNCTUATION_RE.match(fragment):
        return False

    words = _WORD_RE.findall(fragment)

    if not words:
        return False

    if len(fragment) < MIN_FRAGMENT_LENGTH:
        return len(words) == 1 and _is_meaningful_numeric_word(words[0])

    if len(fragment) > MAX_VISUAL_FRAGMENT_LENGTH:
        return False

    if len(words) == 1:
        return _is_meaningful_word(words[0])

    if _is_common_word(words[0]) or _is_common_word(words[-1]):
        return False

    return any(_is_meaningful_word(word) for word in words)


def _is_meaningful_word(word: str) -> bool:
    normalized = normalize_for_alignment(word)

    if normalized.isdigit():
        return _is_meaningful_numeric_word(word)

    return (
        len(normalized) >= MIN_FRAGMENT_LENGTH and normalized not in COMMON_VISUAL_WORDS
    )


def _is_meaningful_numeric_word(word: str) -> bool:
    normalized = normalize_for_alignment(word)
    return normalized.isdigit() and len(normalized) >= 2


def _trim_common_edge_words(words: list[str]) -> list[str]:
    trimmed = list(words)

    while trimmed and _is_common_word(trimmed[0]):
        trimmed.pop(0)

    while trimmed and _is_common_word(trimmed[-1]):
        trimmed.pop()

    return trimmed


def _is_common_word(word: str) -> bool:
    return normalize_for_alignment(word) in COMMON_VISUAL_WORDS


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_items: list[str] = []

    for item in items:
        key = normalize_for_alignment(item)

        if key in seen:
            continue

        seen.add(key)
        unique_items.append(item)

    return unique_items
