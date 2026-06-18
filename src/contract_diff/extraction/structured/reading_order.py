from __future__ import annotations

from contract_diff.extraction.structured.header_footer import (
    classify_header_footer_blocks,
)
from contract_diff.extraction.structured.models import (
    ExtractedPage,
    StructuredDocument,
    TextBlock,
)

EXCLUDED_COMPARISON_BLOCK_TYPES = {"header", "footer", "noise"}


def resolve_reading_order(document: StructuredDocument) -> StructuredDocument:
    classified_document = classify_header_footer_blocks(document)
    pages: list[ExtractedPage] = []

    for page in classified_document.pages:
        sorted_blocks = sorted(page.blocks, key=_reading_order_key)
        pages.append(_page_with_blocks(page, sorted_blocks))

    return _document_with_pages(classified_document, pages)


def get_comparison_blocks(document: StructuredDocument) -> list[TextBlock]:
    return [
        block
        for page in document.pages
        for block in page.blocks
        if block.block_type not in EXCLUDED_COMPARISON_BLOCK_TYPES
        and block.normalized_text
    ]


def _reading_order_key(block: TextBlock) -> tuple[int, float, float]:
    if block.block_type == "header":
        return (-1, block.bbox.y0, block.bbox.x0)

    if block.block_type == "footer":
        return (99, block.bbox.y0, block.bbox.x0)

    if block.column_index is not None:
        return (block.column_index, block.bbox.y0, block.bbox.x0)

    return (0, block.bbox.y0, block.bbox.x0)


def _page_with_blocks(page: ExtractedPage, blocks: list[TextBlock]) -> ExtractedPage:
    return page.model_copy(
        update={
            "text": "\n".join(block.text for block in blocks).strip(),
            "blocks": blocks,
        }
    )


def _document_with_pages(
    document: StructuredDocument,
    pages: list[ExtractedPage],
) -> StructuredDocument:
    return document.model_copy(
        update={
            "text": "\n".join(page.text for page in pages).strip(),
            "pages": pages,
        }
    )
