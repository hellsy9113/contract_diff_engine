from __future__ import annotations

from contract_diff.extraction.structured.models import (
    BoundingBox,
    ExtractedPage,
    StructuredDocument,
    TextBlock,
    TextLine,
    TextSpan,
)
from contract_diff.extraction.structured.structured_pdf_reader import (
    normalize_for_alignment,
)


def make_block(
    text: str,
    *,
    page_index: int = 0,
    block_index: int = 0,
    x0: float = 72,
    y0: float = 72,
    x1: float = 300,
    y1: float | None = None,
    block_type: str = "unknown",
    column_index: int | None = None,
    section_path: list[str] | None = None,
) -> TextBlock:
    resolved_y1 = y1 if y1 is not None else y0 + 18
    bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=resolved_y1)
    span = TextSpan(text=text, bbox=bbox, font="Helvetica", size=10, flags=0)
    line = TextLine(text=text, bbox=bbox, spans=[span], line_index=0)
    return TextBlock(
        text=text,
        normalized_text=normalize_for_alignment(text),
        page_index=page_index,
        block_index=block_index,
        bbox=bbox,
        lines=[line],
        block_type=block_type,
        column_index=column_index,
        section_path=section_path or [],
    )


def make_page(
    blocks: list[TextBlock],
    *,
    page_index: int = 0,
    width: float = 500,
    height: float = 700,
) -> ExtractedPage:
    return ExtractedPage(
        page_index=page_index,
        width=width,
        height=height,
        text="\n".join(block.text for block in blocks),
        blocks=blocks,
        words=[],
    )


def make_document(pages: list[ExtractedPage]) -> StructuredDocument:
    return StructuredDocument(
        page_count=len(pages),
        text="\n".join(page.text for page in pages),
        pages=pages,
        warnings=[],
    )
