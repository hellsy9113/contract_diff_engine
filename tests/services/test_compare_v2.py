from __future__ import annotations

from typing import cast

import fitz  # type: ignore[import-untyped]

from contract_diff.rendering.diagnostics import analyze_rendered_pdf
from contract_diff.services.compare_v2 import compare_pdf_bytes_v2


def make_pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    y = 72

    for paragraph in text.splitlines():
        if not paragraph.strip():
            y += 14
            continue

        page.insert_text((72, y), paragraph, fontsize=11)
        y += 18

    pdf_bytes = cast(bytes, document.tobytes())
    document.close()
    return pdf_bytes


def extract_pdf_text(pdf_bytes: bytes) -> str:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")

    try:
        return "\n".join(page.get_text() for page in document)
    finally:
        document.close()


def test_identical_pdfs_produce_zero_changes() -> None:
    pdf = make_pdf_bytes("Payment shall be made within 30 days.")

    output_pdf, report = compare_pdf_bytes_v2(pdf, pdf)

    assert output_pdf.startswith(b"%PDF")
    assert report.changes == []
    assert report.comparison_quality.added_count == 0


def test_added_sentence_produces_added_change() -> None:
    original = make_pdf_bytes("Payment shall be made within 30 days.")
    revised = make_pdf_bytes(
        "Payment shall be made within 30 days.\n"
        "The buyer shall provide quarterly reports."
    )

    output_pdf, report = compare_pdf_bytes_v2(original, revised)

    assert output_pdf.startswith(b"%PDF")
    assert report.comparison_quality.added_count == 1
    assert any(change.change_type == "added" for change in report.changes)


def test_modified_number_produces_modified_change() -> None:
    original = make_pdf_bytes("Payment shall be made within 30 days.")
    revised = make_pdf_bytes("Payment shall be made within 45 days.")

    output_pdf, report = compare_pdf_bytes_v2(original, revised)

    assert output_pdf.startswith(b"%PDF")
    assert report.comparison_quality.modified_count == 1
    assert report.changes[0].changed_fragments == ["45 days"]


def test_deleted_sentence_produces_deleted_change() -> None:
    original = make_pdf_bytes(
        "Payment shall be made within 30 days.\n"
        "The buyer shall provide quarterly reports."
    )
    revised = make_pdf_bytes("Payment shall be made within 30 days.")

    _, report = compare_pdf_bytes_v2(original, revised)

    assert report.comparison_quality.deleted_count == 1
    assert any(change.change_type == "deleted" for change in report.changes)


def test_output_pdf_is_valid_and_report_is_returned() -> None:
    original = make_pdf_bytes("Payment shall be made within 30 days.")
    revised = make_pdf_bytes("Payment shall be made within 45 days.")

    output_pdf, report = compare_pdf_bytes_v2(original, revised)

    assert extract_pdf_text(output_pdf)
    assert report.comparison_quality.confidence >= 0.0


def test_v2_output_has_no_unwanted_annotation_types() -> None:
    original = make_pdf_bytes("Payment shall be made within 30 days.")
    revised = make_pdf_bytes("Payment shall be made within 45 days.")

    output_pdf, _report = compare_pdf_bytes_v2(original, revised)
    diagnostics = analyze_rendered_pdf(output_pdf)

    assert diagnostics["unwanted_annotation_count"] == 0


def test_page_shift_does_not_create_large_false_positive() -> None:
    original = make_pdf_bytes(
        "Introductory text.\n"
        "Payment shall be made within 30 days."
    )
    revised = make_pdf_bytes(
        "Introductory text.\n\n"
        "Payment shall be made within 30 days."
    )

    _, report = compare_pdf_bytes_v2(original, revised)

    assert len(report.changes) == 0
