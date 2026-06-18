from __future__ import annotations

import re
from collections import defaultdict

from contract_diff.extraction.structured.models import (
    ExtractedPage,
    StructuredDocument,
    TextBlock,
)

HEADER_FOOTER_REPEAT_MIN_PAGES = 2
TOP_MARGIN_RATIO = 0.12
BOTTOM_MARGIN_RATIO = 0.88

PAGE_NUMBER_PATTERNS = (
    re.compile(r"^\d+$"),
    re.compile(r"^page\s+\d+$", re.IGNORECASE),
    re.compile(r"^-\s*\d+\s*-$"),
    re.compile(r"^\d+\s+of\s+\d+$", re.IGNORECASE),
)


def classify_header_footer_blocks(document: StructuredDocument) -> StructuredDocument:
    top_repeated = _repeated_margin_texts(document, margin="top")
    bottom_repeated = _repeated_margin_texts(document, margin="bottom")
    pages: list[ExtractedPage] = []

    for page in document.pages:
        blocks: list[TextBlock] = []

        for block in page.blocks:
            block_type = block.block_type
            normalized = _normalize_layout_text(block.text)

            if is_page_number_text(block.text):
                block_type = "footer"
            elif block_type not in {"header", "footer"}:
                if (
                    _is_top_margin_block(block, page.height)
                    and normalized in top_repeated
                ):
                    block_type = "header"
                elif (
                    _is_bottom_margin_block(block, page.height)
                    and normalized in bottom_repeated
                ):
                    block_type = "footer"

            blocks.append(block.model_copy(update={"block_type": block_type}))

        pages.append(_page_with_blocks(page, blocks))

    return _document_with_pages(document, pages)


def is_page_number_text(text: str) -> bool:
    normalized = _normalize_layout_text(text)
    return any(pattern.match(normalized) for pattern in PAGE_NUMBER_PATTERNS)


def _repeated_margin_texts(
    document: StructuredDocument,
    margin: str,
) -> set[str]:
    page_indexes_by_text: dict[str, set[int]] = defaultdict(set)

    for page in document.pages:
        for block in page.blocks:
            if margin == "top" and not _is_top_margin_block(block, page.height):
                continue

            if margin == "bottom" and not _is_bottom_margin_block(block, page.height):
                continue

            normalized = _normalize_layout_text(block.text)

            if normalized and not is_page_number_text(normalized):
                page_indexes_by_text[normalized].add(page.page_index)

    return {
        text
        for text, page_indexes in page_indexes_by_text.items()
        if len(page_indexes) >= HEADER_FOOTER_REPEAT_MIN_PAGES
    }


def _is_top_margin_block(block: TextBlock, page_height: float) -> bool:
    return block.bbox.y0 <= page_height * TOP_MARGIN_RATIO


def _is_bottom_margin_block(block: TextBlock, page_height: float) -> bool:
    return block.bbox.y1 >= page_height * BOTTOM_MARGIN_RATIO


def _normalize_layout_text(text: str) -> str:
    return " ".join(text.split()).strip().casefold()


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
