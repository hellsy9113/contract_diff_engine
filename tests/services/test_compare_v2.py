from __future__ import annotations

import json
from pathlib import Path
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


def test_single_word_change_reports_word_not_full_paragraph() -> None:
    paragraph = (
        "The tenant shall maintain insurance coverage throughout the term.\n"
        "It shall notify the landlord of cancellation or material adverse event."
    )
    revised_paragraph = paragraph.replace("adverse event.", "adverse breach.")

    _output_pdf, report = compare_pdf_bytes_v2(
        make_pdf_bytes(paragraph),
        make_pdf_bytes(revised_paragraph),
    )

    assert report.comparison_quality.modified_count == 1
    assert report.changes[0].original_text == "event."
    assert report.changes[0].revised_text == "breach."


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
        "Introductory text.\nPayment shall be made within 30 days."
    )
    revised = make_pdf_bytes(
        "Introductory text.\n\nPayment shall be made within 30 days."
    )

    _, report = compare_pdf_bytes_v2(original, revised)

    assert len(report.changes) == 0


def test_debug_diff_writes_sidecar_json(tmp_path: Path) -> None:
    original = make_pdf_bytes("Payment shall be made within 30 days.")
    revised = make_pdf_bytes("Payment shall be made within 45 days.")
    debug_path = tmp_path / "diff-debug.json"

    _, report = compare_pdf_bytes_v2(
        original,
        revised,
        original_filename="original.pdf",
        revised_filename="revised.pdf",
        debug=True,
        debug_output_path=debug_path,
    )
    payload = json.loads(debug_path.read_text(encoding="utf-8"))

    assert debug_path.exists()
    assert payload["original_file"] == "original.pdf"
    assert payload["revised_file"] == "revised.pdf"
    assert payload["total_changes"] == len(report.changes)
    assert payload["changes"][0]["id"] == "CHG-0001"
    assert payload["changes"][0]["type"] == "REPLACE"
    assert payload["changes"][0]["annotation_context"]["inserted_text"] == "45"
