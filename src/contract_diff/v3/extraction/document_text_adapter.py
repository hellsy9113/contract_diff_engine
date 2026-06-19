from __future__ import annotations

from typing import BinaryIO

from contract_diff.extraction.structured.models import ExtractedPage, StructuredDocument
from contract_diff.extraction.structured.pipeline import extract_and_process_pdf
from contract_diff.v3.models.document import V3DocumentText, V3PageText

PdfInput = bytes | BinaryIO


def extract_document_text_v3(
    file: PdfInput,
    filename: str | None = None,
) -> V3DocumentText:
    """Adapt existing structured PDF extraction into v3 document text."""

    pdf_bytes = _read_pdf_bytes(file)
    document = extract_and_process_pdf(pdf_bytes)
    pages = [
        V3PageText(
            page_number=page.page_index + 1,
            text=_page_text(page),
        )
        for page in sorted(document.pages, key=lambda page: page.page_index)
    ]
    full_text = "\n\n".join(page.text for page in pages).strip()

    return V3DocumentText(
        title=_document_title(document),
        full_text=full_text,
        pages=pages,
    )


def _read_pdf_bytes(file: PdfInput) -> bytes:
    if isinstance(file, bytes):
        return file

    position = file.tell()

    try:
        file.seek(0)
        return file.read()
    finally:
        file.seek(position)


def _page_text(page: ExtractedPage) -> str:
    block_texts = [
        "\n".join(line.text for line in block.lines).strip()
        for block in page.blocks
        if block.lines
    ]
    filtered = [text for text in block_texts if text]

    if filtered:
        return "\n\n".join(filtered)

    return page.text.strip()


def _document_title(document: StructuredDocument) -> str | None:
    for page in document.pages:
        for block in page.blocks:
            if block.block_type == "heading":
                text = block.text.strip()

                if text:
                    return text

    return None
