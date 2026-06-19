from __future__ import annotations

import re

from contract_diff.extraction.structured.models import (
    BoundingBox,
    ExtractedPage,
    ExtractedWord,
    StructuredDocument,
    TextBlock,
    WordToken,
)
from contract_diff.extraction.structured.reading_order import (
    EXCLUDED_COMPARISON_BLOCK_TYPES,
)

_PUNCTUATION_TRANSLATION = str.maketrans(
    {
        "\u00ad": "",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\ufffe": "-",
    }
)


def build_word_tokens(
    document: StructuredDocument,
    *,
    include_excluded_blocks: bool = False,
) -> list[WordToken]:
    """Build stable full-document word tokens from structured extraction data."""

    tokens: list[WordToken] = []

    for page in document.pages:
        tokens.extend(
            _page_word_tokens(
                page,
                token_start_index=len(tokens),
                include_excluded_blocks=include_excluded_blocks,
            )
        )

    return tokens


def normalize_word_token_text(text: str) -> str:
    """Normalize a visible PDF word for matching without changing display text."""

    normalized = text.translate(_PUNCTUATION_TRANSLATION)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().casefold()


def _page_word_tokens(
    page: ExtractedPage,
    *,
    token_start_index: int,
    include_excluded_blocks: bool,
) -> list[WordToken]:
    tokens: list[WordToken] = []
    words_by_block = _words_by_block(page.words)

    for block in page.blocks:
        if (
            not include_excluded_blocks
            and block.block_type in EXCLUDED_COMPARISON_BLOCK_TYPES
        ):
            continue

        block_words = words_by_block.get(block.block_index, [])

        for word in sorted(block_words, key=_word_order_key):
            normalized = normalize_word_token_text(word.text)

            if not normalized:
                continue

            token_index = token_start_index + len(tokens)
            block_id = _block_id(block)
            line_id = _line_id(block, word.line_index)
            tokens.append(
                WordToken(
                    id=f"token-{token_index}",
                    text=word.text,
                    normalized=normalized,
                    page_number=page.page_index + 1,
                    bbox=_bbox_tuple(word.bbox),
                    line_id=line_id,
                    block_id=block_id,
                    paragraph_id=_paragraph_id(block),
                    section_heading=_section_heading(block),
                    token_index=token_index,
                )
            )

    if tokens:
        return tokens

    return _fallback_page_tokens(page, token_start_index)


def _fallback_page_tokens(
    page: ExtractedPage,
    token_start_index: int,
) -> list[WordToken]:
    """Tokenize words that cannot be mapped back to a processed block."""

    tokens: list[WordToken] = []
    mapped_word_indexes = {
        word.word_index
        for block in page.blocks
        for word in page.words
        if word.block_index == block.block_index
    }
    unmapped_words = [
        word for word in page.words if word.word_index not in mapped_word_indexes
    ]

    for word in sorted(unmapped_words, key=_word_order_key):
        normalized = normalize_word_token_text(word.text)

        if not normalized:
            continue

        token_index = token_start_index + len(tokens)
        tokens.append(
            WordToken(
                id=f"token-{token_index}",
                text=word.text,
                normalized=normalized,
                page_number=page.page_index + 1,
                bbox=_bbox_tuple(word.bbox),
                line_id=None,
                block_id=None,
                paragraph_id=None,
                section_heading=None,
                token_index=token_index,
            )
        )

    return tokens


def _words_by_block(words: list[ExtractedWord]) -> dict[int, list[ExtractedWord]]:
    by_block: dict[int, list[ExtractedWord]] = {}

    for word in words:
        if word.block_index is None:
            continue

        by_block.setdefault(word.block_index, []).append(word)

    return by_block


def _word_order_key(word: ExtractedWord) -> tuple[int, int, float, float, int]:
    block_index = word.block_index if word.block_index is not None else 10**9
    line_index = word.line_index if word.line_index is not None else 10**9
    return (
        block_index,
        line_index,
        word.bbox.y0,
        word.bbox.x0,
        word.word_index,
    )


def _bbox_tuple(bbox: BoundingBox) -> tuple[float, float, float, float]:
    return (bbox.x0, bbox.y0, bbox.x1, bbox.y1)


def _block_id(block: TextBlock) -> str:
    return f"page-{block.page_index}-block-{block.block_index}"


def _line_id(block: TextBlock, line_index: int | None) -> str | None:
    if line_index is None:
        return None

    return f"{_block_id(block)}-line-{line_index}"


def _paragraph_id(block: TextBlock) -> str | None:
    if block.block_type not in {"paragraph", "list_item", "table_candidate"}:
        return None

    return _block_id(block)


def _section_heading(block: TextBlock) -> str | None:
    if block.section_path:
        return block.section_path[-1]

    return None
