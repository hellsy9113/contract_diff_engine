from __future__ import annotations

import re
from difflib import SequenceMatcher

COMMON_SEARCH_WORDS = frozenset(
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
        "to",
        "with",
    }
)
MODIFIED_BLOCK_SIMILARITY_THRESHOLD = 0.75
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?|[^\w\s]")
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?")
_NO_SPACE_BEFORE = frozenset({".", ",", ";", ":", "!", "?", ")", "]", "}"})
_NO_SPACE_AFTER = frozenset({"(", "[", "{"})


def normalize_for_alignment(text: str) -> str:
    """
    Normalize text for matching/alignment only.

    The normalized value is intentionally not used for rendering because the PDF
    renderer needs the original extracted text and coordinates.
    """

    normalized = text.replace("\u00ad", "")
    normalized = normalized.replace("￾", "-")
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.replace("‘", "'").replace("’", "'")
    normalized = normalized.replace("‐", "-").replace("‑", "-")
    normalized = normalized.replace("–", "-").replace("—", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().casefold()


def tokenize_for_diff(text: str) -> list[str]:
    """
    Tokenize text into words and punctuation for deterministic inner diffs.
    """

    return _TOKEN_RE.findall(text)


def get_changed_fragments(original_text: str, revised_text: str) -> list[str]:
    """
    Return only revised-side inserted/replaced fragments from a modified block.
    """

    original_tokens = tokenize_for_diff(original_text)
    revised_tokens = tokenize_for_diff(revised_text)
    original_keys = [normalize_for_alignment(token) for token in original_tokens]
    revised_keys = [normalize_for_alignment(token) for token in revised_tokens]
    matcher = SequenceMatcher(None, original_keys, revised_keys)
    fragments: list[str] = []

    for tag, _original_start, _original_end, revised_start, revised_end in (
        matcher.get_opcodes()
    ):
        if tag in {"equal", "delete"}:
            continue

        fragment = _clean_changed_fragment(
            _join_tokens(revised_tokens[revised_start:revised_end])
        )

        if normalize_for_alignment(fragment):
            fragments.append(fragment)

    return fragments


def build_search_fragments(changed_text: str) -> list[str]:
    """
    Convert changed text into safe searchable PDF fragments.

    Full paragraphs and tiny/common standalone words create noisy highlights, so
    this returns compact phrases and ignores fragments that are unlikely to be
    useful search targets.
    """

    normalized = _normalize_render_variant(changed_text)
    words = _WORD_RE.findall(normalized)
    fragments: list[str] = []

    if _is_searchable_phrase(normalized):
        fragments.append(normalized)

    if len(words) == 1:
        word = words[0]

        if _is_searchable_word(word):
            fragments.append(word)

        return _unique(fragments)

    for window_size in (6, 5, 4, 3, 2):
        if len(words) < window_size:
            continue

        for start in range(0, len(words) - window_size + 1):
            phrase = " ".join(words[start : start + window_size])

            if _is_searchable_phrase(phrase):
                fragments.append(phrase)

    return _unique(fragments)


def similarity_ratio(left: str, right: str) -> float:
    left_normalized = normalize_for_alignment(left)
    right_normalized = normalize_for_alignment(right)

    if not left_normalized and not right_normalized:
        return 1.0

    if not left_normalized or not right_normalized:
        return 0.0

    return SequenceMatcher(None, left_normalized, right_normalized).ratio()


def _normalize_render_variant(text: str) -> str:
    normalized = text.replace("\u00ad", "")
    normalized = normalized.replace("￾", "-")
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.replace("‘", "'").replace("’", "'")
    normalized = normalized.replace("‐", "-").replace("‑", "-")
    normalized = normalized.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", normalized).strip()


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


def _clean_changed_fragment(fragment: str) -> str:
    """
    Trim punctuation artifacts created by token alignment.

    SequenceMatcher can align sentence punctuation with a later equal sentence,
    leaving the inserted phrase with a leading "." or ",". Search fragments are
    more reliable when they start with the actual changed words.
    """

    return fragment.strip().lstrip(".,;:!? ").strip()


def _is_searchable_phrase(phrase: str) -> bool:
    words = _WORD_RE.findall(phrase)

    if not words:
        return False

    if len(words) == 1:
        return _is_searchable_word(words[0])

    if len(phrase) > 96:
        return False

    return any(_is_searchable_word(word) for word in words)


def _is_searchable_word(word: str) -> bool:
    normalized = normalize_for_alignment(word)
    if normalized.isdigit():
        return len(normalized) >= 2

    return len(normalized) >= 3 and normalized not in COMMON_SEARCH_WORDS


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_items: list[str] = []

    for item in items:
        if item in seen:
            continue

        seen.add(item)
        unique_items.append(item)

    return unique_items
