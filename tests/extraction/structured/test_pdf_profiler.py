from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import cast

import fitz  # type: ignore[import-untyped]

from contract_diff.extraction.structured.models import PdfIntakeReport
from contract_diff.extraction.structured.pdf_profiler import profile_pdf


def test_profile_valid_simple_text_pdf() -> None:
    report = profile_pdf(_text_pdf("This agreement contains payment terms."))

    assert report.is_valid_pdf is True
    assert report.page_count == 1
    assert report.is_encrypted is False
    assert report.has_extractable_text is True
    assert report.text_char_count > 0
    assert report.word_count >= 5
    assert report.image_count == 0
    assert report.annotation_count == 0
    assert report.scanned_likelihood == 0


def test_profile_invalid_pdf_bytes_returns_invalid_report() -> None:
    report = profile_pdf(b"not a pdf")

    assert report.is_valid_pdf is False
    assert report.page_count == 0
    assert report.has_extractable_text is False
    assert report.warnings


def test_profile_near_empty_pdf_warns_about_little_text() -> None:
    report = profile_pdf(_empty_pdf())

    assert report.is_valid_pdf is True
    assert report.page_count == 1
    assert report.has_extractable_text is False
    assert "PDF has very little extractable text" in report.warnings
    assert "PDF appears scanned or image-heavy" not in report.warnings


def test_profile_image_heavy_low_text_pdf() -> None:
    report = profile_pdf(_image_pdf())

    assert report.is_valid_pdf is True
    assert report.image_count == 1
    assert report.text_char_count == 0
    assert report.scanned_likelihood >= 0.65
    assert "PDF appears scanned or image-heavy" in report.warnings


def test_profile_pdf_with_highlight_annotation() -> None:
    report = profile_pdf(_annotated_pdf())

    assert report.annotation_count == 1
    assert report.highlight_annotation_count == 1
    assert "PDF has existing annotations" in report.warnings


def test_profile_pdf_script_can_be_imported_and_called(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(_text_pdf("A script import smoke test."))
    profile_pdf_file = _load_profile_pdf_file()

    report = profile_pdf_file(pdf_path)

    assert report.is_valid_pdf is True
    assert report.page_count == 1


def test_profile_table_like_pdf_sets_table_warning() -> None:
    report = profile_pdf(_table_like_pdf())

    assert report.table_likelihood >= 0.55
    assert "PDF may contain tables" in report.warnings


def test_profile_column_like_pdf_sets_column_warning() -> None:
    report = profile_pdf(_two_column_pdf())

    assert report.column_likelihood >= 0.55
    assert "PDF may contain multiple columns" in report.warnings


def _text_pdf(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page(width=400, height=400)
    page.insert_text((72, 72), text, fontsize=11)
    data = bytes(document.tobytes())
    document.close()
    return data


def _load_profile_pdf_file() -> Callable[[Path], PdfIntakeReport]:
    script_path = Path("scripts/profile_pdf.py")
    spec = importlib.util.spec_from_file_location("profile_pdf_script", script_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    profile_pdf_file = getattr(module, "profile_pdf_file")
    assert callable(profile_pdf_file)
    return cast(Callable[[Path], PdfIntakeReport], profile_pdf_file)


def _empty_pdf() -> bytes:
    document = fitz.open()
    document.new_page(width=400, height=400)
    data = bytes(document.tobytes())
    document.close()
    return data


def _image_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page(width=400, height=400)
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 120, 120), False)
    pixmap.clear_with(240)
    page.insert_image(fitz.Rect(72, 72, 300, 300), pixmap=pixmap)
    data = bytes(document.tobytes())
    document.close()
    return data


def _annotated_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page(width=400, height=400)
    page.insert_text((72, 72), "Annotated contract text", fontsize=11)
    rect = page.search_for("contract")[0]
    annotation = page.add_highlight_annot(rect)
    annotation.update()
    data = bytes(document.tobytes())
    document.close()
    return data


def _table_like_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page(width=400, height=400)

    for row in range(12):
        y = 72 + row * 18
        for column, text in enumerate(("Fee", "Term", "Cap")):
            page.insert_text((72 + column * 80, y), f"{text} {row}", fontsize=9)

    data = bytes(document.tobytes())
    document.close()
    return data


def _two_column_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page(width=500, height=500)

    for index in range(5):
        page.insert_text(
            (72, 72 + index * 32),
            f"Left clause {index} contains several words.",
            fontsize=10,
        )
        page.insert_text(
            (290, 72 + index * 32),
            f"Right clause {index} contains several words.",
            fontsize=10,
        )

    data = bytes(document.tobytes())
    document.close()
    return data
