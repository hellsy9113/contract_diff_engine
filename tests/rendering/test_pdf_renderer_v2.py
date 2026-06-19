from __future__ import annotations

from typing import Any, cast

import fitz  # type: ignore[import-untyped]

from contract_diff.comparison.structured_changes import Change, Location
from contract_diff.extraction.structured.models import BoundingBox, WordToken
from contract_diff.extraction.structured.word_tokens import normalize_word_token_text
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


def make_location(bbox: BoundingBox | None = None) -> Location:
    return Location(page_index=0, block_index=0, bbox=bbox, section_path=[])


def make_change(
    change_type: str,
    *,
    original_text: str | None = "Payment shall be made within 30 days.",
    revised_text: str | None = "Payment shall be made within 45 days.",
    changed_fragments: list[str] | None = None,
    confidence: float = 0.95,
    metadata: dict[str, Any] | None = None,
    revised_location: Location | None = None,
    section_path: list[str] | None = None,
) -> Change:
    return Change(
        change_id="CHG-0001",
        change_type=change_type,  # type: ignore[arg-type]
        original_text=original_text,
        revised_text=revised_text,
        original_location=make_location(),
        revised_location=(
            revised_location if revised_location is not None else make_location()
        ),
        changed_fragments=changed_fragments or [],
        confidence=confidence,
        section_path=section_path or [],
        metadata=metadata or {},
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


def test_word_diff_single_word_replacement_creates_small_highlight() -> None:
    token = make_word_token("must", x0=128, x1=154)
    output = render_changes_to_pdf(
        make_pdf_bytes("The tenant must pay rent monthly."),
        [
            make_change(
                "modified",
                original_text="shall",
                revised_text="must",
                changed_fragments=["must"],
                metadata=word_diff_metadata([token]),
            )
        ],
    )
    document = fitz.open(stream=output, filetype="pdf")

    try:
        page = document[0]
        annotation = page.first_annot

        assert annotation is not None
        assert annotation.type[1] == "Highlight"
        assert float(annotation.rect.width) < 45
    finally:
        document.close()


def test_word_diff_adjacent_inserted_words_create_compact_highlight() -> None:
    tokens = [
        make_word_token("on", x0=184, x1=198),
        make_word_token("time", x0=200, x1=226, token_index=1),
    ]
    output = render_changes_to_pdf(
        make_pdf_bytes("The tenant shall pay rent on time monthly."),
        [
            make_change(
                "added",
                original_text=None,
                revised_text="on time",
                changed_fragments=["on time"],
                metadata=word_diff_metadata(tokens),
            )
        ],
    )
    document = fitz.open(stream=output, filetype="pdf")

    try:
        page = document[0]
        annotation = page.first_annot

        assert annotation is not None
        assert annotation.type[1] == "Highlight"
        assert float(annotation.rect.width) < 60
    finally:
        document.close()


def test_renderer_v2_uses_annotation_context_content() -> None:
    output = render_changes_to_pdf(
        make_pdf_bytes(),
        [
            make_change(
                "modified",
                changed_fragments=["45 days"],
                metadata={
                    "annotation_context": {
                        "before_word": "within",
                        "deleted_text": "30",
                        "inserted_text": "45",
                        "after_word": "days.",
                        "display_markdown": "within ~~30~~ 45 days.",
                        "plain_text": "within 30 45 days.",
                    }
                },
                section_path=["1. Introduction"],
            )
        ],
    )
    document = fitz.open(stream=output, filetype="pdf")

    try:
        page = document[0]
        annotation = page.first_annot

        assert annotation is not None
        assert annotation.info["content"] == (
            "CHG-0001 | REPLACE | Page 1 | 1. Introduction\n"
            "Context: within [DELETED: 30] 45 days."
        )
    finally:
        document.close()


def test_renderer_v2_formats_insert_annotation_context() -> None:
    output = render_changes_to_pdf(
        make_pdf_bytes("[14]. Ultimately, this research supports 2."),
        [
            make_change(
                "added",
                original_text=None,
                revised_text="Ultimately, this research supports",
                changed_fragments=["Ultimately, this research supports"],
                metadata={
                    "annotation_context": {
                        "before_word": "[14].",
                        "deleted_text": None,
                        "inserted_text": "Ultimately, this research supports",
                        "after_word": "2.",
                        "display_markdown": (
                            "[14]. ++Ultimately, this research supports++ 2."
                        ),
                        "plain_text": ("[14]. Ultimately, this research supports 2."),
                    }
                },
                section_path=["1. Introduction"],
            )
        ],
    )
    document = fitz.open(stream=output, filetype="pdf")

    try:
        page = document[0]
        annotation = page.first_annot

        assert annotation is not None
        assert annotation.info["content"] == (
            "CHG-0001 | INSERT | Page 1 | 1. Introduction\n"
            "Context: [14]. ++Ultimately, this research supports++ 2."
        )
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


def test_word_diff_deleted_change_creates_small_anchor_without_highlight() -> None:
    anchor = BoundingBox(x0=140, y0=88, x1=156, y1=102)
    output = render_changes_to_pdf(
        make_pdf_bytes("The tenant shall pay monthly."),
        [
            make_change(
                "deleted",
                original_text="rent",
                revised_text=None,
                changed_fragments=[],
                revised_location=make_location(anchor),
                metadata={
                    "comparison_strategy": "document_word_diff",
                    "revised_tokens": [],
                    "annotation_context": {
                        "before_word": "pay",
                        "deleted_text": "rent",
                        "inserted_text": None,
                        "after_word": "monthly.",
                        "display_markdown": "pay ~~rent~~ monthly.",
                        "plain_text": "pay rent monthly.",
                    },
                },
            )
        ],
    )
    diagnostics = analyze_rendered_pdf(output)
    document = fitz.open(stream=output, filetype="pdf")

    try:
        page = document[0]
        annotation = page.first_annot

        assert diagnostics["annotation_counts"].get("Highlight", 0) == 0
        assert diagnostics["annotation_counts"].get("Underline", 0) == 1
        assert annotation is not None
        assert float(annotation.rect.width) < 35
        assert annotation.info["content"] == (
            "CHG-0001 | DELETE | Page 1\nContext: pay [DELETED: rent] monthly."
        )
    finally:
        document.close()


def test_known_pki_delete_renders_marker_not_paragraph_highlight() -> None:
    anchor = BoundingBox(x0=72, y0=88, x1=108, y1=102)
    output = render_changes_to_pdf(
        make_pdf_bytes("[28]. (PKI), the trust framework"),
        [
            make_change(
                "deleted",
                original_text="Public Key Infrastructure",
                revised_text=None,
                changed_fragments=[],
                revised_location=make_location(anchor),
                metadata={
                    "comparison_strategy": "document_word_diff",
                    "delete_anchor_strategy": ("nearest_surviving_revised_token_after"),
                    "delete_anchor_token_id": "token-1",
                    "revised_tokens": [],
                    "annotation_context": {
                        "before_word": "[28].",
                        "deleted_text": "Public Key Infrastructure",
                        "inserted_text": None,
                        "after_word": "(PKI),",
                        "display_markdown": (
                            "[28]. ~~Public Key Infrastructure~~ (PKI),"
                        ),
                        "plain_text": "[28]. Public Key Infrastructure (PKI),",
                    },
                },
            )
        ],
    )
    diagnostics = analyze_rendered_pdf(output)
    document = fitz.open(stream=output, filetype="pdf")

    try:
        page = document[0]
        annotation = page.first_annot

        assert diagnostics["annotation_counts"].get("Highlight", 0) == 0
        assert diagnostics["annotation_counts"].get("Underline", 0) == 1
        assert annotation is not None
        assert annotation.info["content"] == (
            "CHG-0001 | DELETE | Page 1\n"
            "Context: [28]. [DELETED: Public Key Infrastructure] (PKI),"
        )
    finally:
        document.close()


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


def make_word_token(
    text: str,
    *,
    x0: float,
    x1: float,
    token_index: int = 0,
    line_id: str = "page-0-block-0-line-0",
) -> WordToken:
    return WordToken(
        id=f"token-{token_index}",
        text=text,
        normalized=normalize_word_token_text(text),
        page_number=1,
        bbox=(x0, 88, x1, 102),
        line_id=line_id,
        block_id="page-0-block-0",
        paragraph_id="page-0-block-0",
        section_heading=None,
        token_index=token_index,
    )


def word_diff_metadata(tokens: list[WordToken]) -> dict[str, Any]:
    return {
        "comparison_strategy": "document_word_diff",
        "revised_tokens": [token.model_dump() for token in tokens],
        "annotation_context": {
            "before_word": "tenant",
            "deleted_text": "shall",
            "inserted_text": "must",
            "after_word": "pay",
            "display_markdown": "tenant ~~shall~~ must pay",
            "plain_text": "tenant shall must pay",
        },
    }
