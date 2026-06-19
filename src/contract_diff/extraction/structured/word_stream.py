from __future__ import annotations

from contract_diff.extraction.structured.models import (
    DocumentWordStream,
    ExtractedPage,
    PageInfo,
    StructuredDocument,
    WordToken,
)
from contract_diff.extraction.structured.word_tokens import build_word_tokens


def build_document_word_stream(
    document: StructuredDocument,
    *,
    source_file_name: str | None = None,
    include_excluded_blocks: bool = False,
) -> DocumentWordStream:
    """Build a full-document token stream for document-level comparison."""

    tokens = _stream_tokens(
        document,
        include_excluded_blocks=include_excluded_blocks,
    )
    pages = [_page_info(page, tokens) for page in document.pages]

    return DocumentWordStream(
        tokens=tokens,
        pages=pages,
        source_file_name=source_file_name,
    )


def _stream_tokens(
    document: StructuredDocument,
    *,
    include_excluded_blocks: bool,
) -> list[WordToken]:
    if document.word_tokens and not include_excluded_blocks:
        return sorted(document.word_tokens, key=lambda token: token.token_index)

    return build_word_tokens(
        document,
        include_excluded_blocks=include_excluded_blocks,
    )


def _page_info(page: ExtractedPage, tokens: list[WordToken]) -> PageInfo:
    page_number = page.page_index + 1
    page_token_indexes = [
        token.token_index for token in tokens if token.page_number == page_number
    ]

    if page_token_indexes:
        token_start_index = min(page_token_indexes)
        token_end_index = max(page_token_indexes) + 1
    else:
        token_start_index = None
        token_end_index = None

    return PageInfo(
        page_number=page_number,
        page_index=page.page_index,
        width=page.width,
        height=page.height,
        token_start_index=token_start_index,
        token_end_index=token_end_index,
    )
