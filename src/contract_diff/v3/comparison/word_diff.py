from __future__ import annotations

import re
from difflib import SequenceMatcher

from contract_diff.extraction.structured.word_tokens import normalize_word_token_text
from contract_diff.v3.models import V3DiffToken, V3DiffTokenType

_TOKEN_RE = re.compile(r"\s+|\w+|[^\w\s]", re.UNICODE)


class _TextToken:
    def __init__(self, text: str, normalized: str) -> None:
        self.text = text
        self.normalized = normalized


def diff_clause_words(
    original_text: str | None,
    revised_text: str | None,
) -> list[V3DiffToken]:
    """Create frontend-ready word diff tokens for one clause."""

    if not original_text and not revised_text:
        return []

    if not original_text:
        return [V3DiffToken(type="insert", text=revised_text or "")]

    if not revised_text:
        return [V3DiffToken(type="delete", text=original_text)]

    original_tokens = _tokenize(original_text)
    revised_tokens = _tokenize(revised_text)
    matcher = SequenceMatcher(
        None,
        [token.normalized for token in original_tokens],
        [token.normalized for token in revised_tokens],
        autojunk=False,
    )
    chunks: list[V3DiffToken] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            _append_chunk(chunks, "equal", _join_tokens(revised_tokens[j1:j2]))
            continue

        if tag in {"replace", "delete"}:
            _append_chunk(chunks, "delete", _join_tokens(original_tokens[i1:i2]))

        if tag in {"replace", "insert"}:
            _append_chunk(chunks, "insert", _join_tokens(revised_tokens[j1:j2]))

    return _normalize_chunk_boundaries(chunks)


def _tokenize(text: str) -> list[_TextToken]:
    tokens: list[_TextToken] = []

    for match in _TOKEN_RE.finditer(text):
        value = match.group(0)
        normalized = " " if value.isspace() else normalize_word_token_text(value)
        tokens.append(_TextToken(text=value, normalized=normalized))

    return tokens


def _join_tokens(tokens: list[_TextToken]) -> str:
    return "".join(token.text for token in tokens)


def _append_chunk(
    chunks: list[V3DiffToken],
    token_type: V3DiffTokenType,
    text: str,
) -> None:
    if not text:
        return

    if chunks and chunks[-1].type == token_type:
        previous = chunks[-1]
        chunks[-1] = previous.model_copy(update={"text": previous.text + text})
        return

    chunks.append(V3DiffToken(type=token_type, text=text))


def _normalize_chunk_boundaries(chunks: list[V3DiffToken]) -> list[V3DiffToken]:
    normalized = [chunk.model_copy() for chunk in chunks]

    for index, chunk in enumerate(normalized):
        if chunk.type == "equal":
            continue

        if index + 1 < len(normalized) and chunk.text.endswith((" ", "\n", "\t")):
            stripped = chunk.text.rstrip(" \n\t")
            suffix = chunk.text[len(stripped) :]
            next_chunk = normalized[index + 1]
            normalized[index] = chunk.model_copy(update={"text": stripped})
            normalized[index + 1] = next_chunk.model_copy(
                update={"text": suffix + next_chunk.text}
            )
            chunk = normalized[index]

        if index > 0 and chunk.text.startswith((" ", "\n", "\t")):
            stripped = chunk.text.lstrip(" \n\t")
            prefix = chunk.text[: len(chunk.text) - len(stripped)]
            previous_chunk = normalized[index - 1]
            normalized[index] = chunk.model_copy(update={"text": stripped})
            normalized[index - 1] = previous_chunk.model_copy(
                update={"text": previous_chunk.text + prefix}
            )

    return [chunk for chunk in normalized if chunk.text]
