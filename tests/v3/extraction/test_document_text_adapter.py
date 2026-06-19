from __future__ import annotations

from io import BytesIO

import fitz  # type: ignore[import-untyped]
import pytest

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
from contract_diff.v3.extraction import document_text_adapter
from contract_diff.v3.extraction.document_text_adapter import extract_document_text_v3
from contract_diff.v3.models import V3DocumentText


def test_adapter_returns_v3_document_text() -> None:
    document = extract_document_text_v3(_text_pdf(["Payment terms apply."]))

    assert isinstance(document, V3DocumentText)
    assert document.title is None
    assert document.full_text


def test_adapter_returns_ordered_pages_and_full_text() -> None:
    document = extract_document_text_v3(
        _text_pdf(["First page clause.", "Second page clause."])
    )

    assert [page.page_number for page in document.pages] == [1, 2]
    assert "First page clause." in document.pages[0].text
    assert "Second page clause." in document.pages[1].text
    assert document.full_text.index("First page clause.") < document.full_text.index(
        "Second page clause."
    )


def test_adapter_preserves_page_numbers() -> None:
    document = extract_document_text_v3(
        _text_pdf(["Page one.", "Page two.", "Page three."])
    )

    assert [page.page_number for page in document.pages] == [1, 2, 3]


def test_adapter_preserves_file_like_stream_position() -> None:
    stream = BytesIO(_text_pdf(["Payment terms apply."]))
    stream.seek(5)

    document = extract_document_text_v3(stream)

    assert document.full_text
    assert stream.tell() == 5


def test_adapter_reuses_existing_structured_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bytes] = []

    def fake_extract_and_process_pdf(pdf_bytes: bytes) -> StructuredDocument:
        calls.append(pdf_bytes)
        return make_document(
            [
                make_page(
                    [make_block("Adapted first page.", page_index=0)],
                    page_index=0,
                ),
                make_page(
                    [make_block("Adapted second page.", page_index=1)],
                    page_index=1,
                ),
            ]
        )

    monkeypatch.setattr(
        document_text_adapter,
        "extract_and_process_pdf",
        fake_extract_and_process_pdf,
    )

    document = extract_document_text_v3(b"%PDF fake")

    assert calls == [b"%PDF fake"]
    assert [page.text for page in document.pages] == [
        "Adapted first page.",
        "Adapted second page.",
    ]


def _text_pdf(page_texts: list[str]) -> bytes:
    document = fitz.open()

    for page_text in page_texts:
        page = document.new_page(width=400, height=400)
        page.insert_text((72, 72), page_text, fontsize=11)

    data = bytes(document.tobytes())
    document.close()
    return data


def make_block(text: str, *, page_index: int) -> TextBlock:
    bbox = BoundingBox(x0=72, y0=72, x1=300, y1=90)
    span = TextSpan(text=text, bbox=bbox, font="Helvetica", size=10, flags=0)
    line = TextLine(text=text, bbox=bbox, spans=[span], line_index=0)
    return TextBlock(
        text=text,
        normalized_text=normalize_for_alignment(text),
        page_index=page_index,
        block_index=0,
        bbox=bbox,
        lines=[line],
        block_type="paragraph",
        column_index=None,
        section_path=[],
    )


def make_page(blocks: list[TextBlock], *, page_index: int) -> ExtractedPage:
    return ExtractedPage(
        page_index=page_index,
        width=400,
        height=400,
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
