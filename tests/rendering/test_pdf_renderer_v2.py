from __future__ import annotations

from typing import cast

import fitz  # type: ignore[import-untyped]

from contract_diff.comparison.structured_changes import Change, Location
from contract_diff.rendering.diagnostics import analyze_rendered_pdf
from contract_diff.rendering.pdf_renderer_v2 import render_changes_to_pdf
from contract_diff.rendering.styles.v2 import MAX_HIGHLIGHTS_PER_PAGE


def make_pdf_bytes(text: str = "Payment shall be made within 45 days.") -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 90), text, fontsize=12)
    pdf_bytes = cast(bytes, document.tobytes())
    document.close()
    return pdf_bytes


def make_location() -> Location:
    return Location(page_index=0, block_index=0, bbox=None, section_path=[])


def make_change(
    change_type: str,
    *,
    original_text: str | None = "Payment shall be made within 30 days.",
    revised_text: str | None = "Payment shall be made within 45 days.",
    changed_fragments: list[str] | None = None,
    confidence: float = 0.95,
) -> Change:
    return Change(
        change_id="CHG-0001",
        change_type=change_type,  # type: ignore[arg-type]
        original_text=original_text,
        revised_text=revised_text,
        original_location=make_location(),
        revised_location=make_location(),
        changed_fragments=changed_fragments or [],
        confidence=confidence,
        section_path=[],
        metadata={},
    )


def test_renderer_v2_output_starts_with_pdf_header() -> None:
    output = render_changes_to_pdf(
        make_pdf_bytes(),
        [make_change("modified", changed_fragments=["45 days"])],
    )

    assert output.startswith(b"%PDF")


def test_renderer_v2_creates_no_unwanted_annotation_types() -> None:
    output = render_changes_to_pdf(
        make_pdf_bytes(),
        [
            make_change("added"),
            make_change("modified", changed_fragments=["45 days"]),
        ],
    )

    diagnostics = analyze_rendered_pdf(output)

    assert diagnostics["unwanted_annotation_count"] == 0
    assert diagnostics["annotation_counts"].get("Text", 0) == 0
    assert diagnostics["annotation_counts"].get("Square", 0) == 0
    assert diagnostics["annotation_counts"].get("FreeText", 0) == 0
    assert diagnostics["annotation_counts"].get("Rect", 0) == 0


def test_added_change_creates_highlight() -> None:
    output = render_changes_to_pdf(
        make_pdf_bytes("A new payment covenant applies."),
        [
            make_change(
                "added",
                original_text=None,
                revised_text="A new payment covenant applies.",
            )
        ],
    )

    diagnostics = analyze_rendered_pdf(output)

    assert diagnostics["annotation_counts"].get("Highlight", 0) == 1
    assert diagnostics["highlights_by_page"] == {1: 1}


def test_modified_change_uses_changed_fragments_not_full_line() -> None:
    output = render_changes_to_pdf(
        make_pdf_bytes(),
        [make_change("modified", changed_fragments=["45 days"])],
    )
    document = fitz.open(stream=output, filetype="pdf")

    try:
        page = document[0]
        annotation = page.first_annot

        assert annotation is not None
        assert annotation.type[1] == "Highlight"
        assert float(annotation.rect.width) < 90
    finally:
        document.close()


def test_deleted_change_does_not_create_body_square() -> None:
    output = render_changes_to_pdf(
        make_pdf_bytes(),
        [
            make_change(
                "deleted",
                revised_text=None,
                changed_fragments=[],
            )
        ],
    )

    diagnostics = analyze_rendered_pdf(output)

    assert diagnostics["annotation_counts"].get("Square", 0) == 0
    assert diagnostics["annotation_counts"].get("FreeText", 0) == 0


def test_duplicate_rects_are_skipped() -> None:
    output = render_changes_to_pdf(
        make_pdf_bytes(),
        [make_change("modified", changed_fragments=["45 days", "45 days"])],
    )

    diagnostics = analyze_rendered_pdf(output)

    assert diagnostics["annotation_counts"].get("Highlight", 0) == 1


def test_dense_page_warning_diagnostics_work() -> None:
    document = fitz.open()
    page = document.new_page(width=300, height=300)

    for index in range(MAX_HIGHLIGHTS_PER_PAGE + 1):
        y0 = 10 + (index * 10)
        highlight = page.add_highlight_annot(fitz.Rect(20, y0, 250, y0 + 6))
        highlight.update()

    pdf_bytes = cast(bytes, document.tobytes())
    document.close()

    diagnostics = analyze_rendered_pdf(pdf_bytes)

    assert diagnostics["max_highlights_on_page"] == MAX_HIGHLIGHTS_PER_PAGE + 1
    assert diagnostics["dense_pages"] == [1]
