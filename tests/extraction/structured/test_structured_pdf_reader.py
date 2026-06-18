from __future__ import annotations

import importlib.util
from pathlib import Path

import fitz  # type: ignore[import-untyped]
import pytest

from contract_diff.extraction.exceptions.extraction import InvalidDocumentError
from contract_diff.extraction.structured.models import BoundingBox
from contract_diff.extraction.structured.structured_pdf_reader import (
    bbox_from_tuple,
    extract_structured_pdf,
    merge_bboxes,
    normalize_for_alignment,
)


def test_extract_structured_pdf_reports_page_count() -> None:
    document = extract_structured_pdf(_text_pdf(["Payment terms apply."]))

    assert document.page_count == 1
    assert len(document.pages) == 1
    assert document.pages[0].page_index == 0


def test_extract_structured_pdf_extracts_blocks() -> None:
    document = extract_structured_pdf(_text_pdf(["Payment terms apply."]))

    assert document.pages[0].blocks
    assert "Payment terms apply" in document.pages[0].blocks[0].text
    assert document.pages[0].blocks[0].block_type == "unknown"
    assert document.pages[0].blocks[0].column_index is None
    assert document.pages[0].blocks[0].section_path == []


def test_extract_structured_pdf_extracts_words() -> None:
    document = extract_structured_pdf(_text_pdf(["Payment terms apply."]))
    words = document.pages[0].words

    assert [word.text for word in words[:3]] == ["Payment", "terms", "apply."]
    assert words[0].page_index == 0
    assert words[0].word_index == 0
    assert words[0].block_index is not None
    assert words[0].line_index is not None


def test_extract_structured_pdf_preserves_bboxes() -> None:
    document = extract_structured_pdf(_text_pdf(["Payment terms apply."]))
    block = document.pages[0].blocks[0]
    line = block.lines[0]
    span = line.spans[0]
    word = document.pages[0].words[0]

    assert block.bbox.x1 > block.bbox.x0
    assert line.bbox.y1 > line.bbox.y0
    assert span.bbox.x1 > span.bbox.x0
    assert word.bbox.y1 > word.bbox.y0


def test_extract_structured_pdf_populates_normalized_text() -> None:
    document = extract_structured_pdf(_text_pdf(["  Payment    TERMS apply.  "]))
    block = document.pages[0].blocks[0]

    assert block.normalized_text == "payment terms apply."
    assert normalize_for_alignment(" Payment\nTERMS\tapply. ") == (
        "payment terms apply."
    )


def test_extract_structured_pdf_handles_multi_page_pdf() -> None:
    document = extract_structured_pdf(
        _text_pdf(["First page clause.", "Second page clause."])
    )

    assert document.page_count == 2
    assert len(document.pages) == 2
    assert "First page clause." in document.text
    assert "Second page clause." in document.text
    assert document.pages[1].page_index == 1
    assert document.pages[1].blocks


def test_extract_structured_pdf_raises_invalid_document_for_bad_bytes() -> None:
    with pytest.raises(InvalidDocumentError):
        extract_structured_pdf(b"not a pdf")


def test_bbox_helpers_build_and_merge_boxes() -> None:
    box = bbox_from_tuple((1, 2, 3, 4))
    merged = merge_bboxes([box, BoundingBox(x0=0, y0=3, x1=10, y1=8)])

    assert box == BoundingBox(x0=1, y0=2, x1=3, y1=4)
    assert merged == BoundingBox(x0=0, y0=2, x1=10, y1=8)


def test_extract_structured_pdf_script_can_be_imported() -> None:
    script_path = Path("scripts/extract_structured_pdf.py")
    spec = importlib.util.spec_from_file_location("extract_structured_pdf", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert callable(getattr(module, "main"))


def _text_pdf(page_texts: list[str]) -> bytes:
    document = fitz.open()

    for page_text in page_texts:
        page = document.new_page(width=400, height=400)
        page.insert_text((72, 72), page_text, fontsize=11)

    data = bytes(document.tobytes())
    document.close()
    return data
