import fitz  # type: ignore[import-untyped]
import pytest

from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.enums.highlight_style import HighlightStyle
from contract_diff.rendering.services.highlight_renderer import HighlightRenderer
from contract_diff.rendering.styles.pdf_colors import GREEN, YELLOW
from tests.rendering.helpers import make_annotation, make_pdf_bytes, make_span_box


def test_modified_annotation_creates_yellow_highlight() -> None:
    document = fitz.open(stream=make_pdf_bytes(), filetype="pdf")
    annotation = make_annotation(
        AnnotationType.MODIFIED,
        HighlightStyle.MODIFIED_HIGHLIGHT,
    )

    warnings = HighlightRenderer().render(
        document,
        annotation,
        {"span-rev-1": make_span_box()},
    )

    page = document[0]
    annotations = list(page.annots() or [])
    assert warnings == ()
    assert annotations[0].type[1] == "Highlight"
    assert annotations[0].colors["stroke"] == pytest.approx(YELLOW)
    document.close()


def test_added_annotation_creates_green_highlight() -> None:
    document = fitz.open(stream=make_pdf_bytes(), filetype="pdf")
    annotation = make_annotation(
        AnnotationType.ADDED,
        HighlightStyle.ADDED_HIGHLIGHT,
    )

    warnings = HighlightRenderer().render(
        document,
        annotation,
        {"span-rev-1": make_span_box()},
    )

    page = document[0]
    annotations = list(page.annots() or [])
    assert warnings == ()
    assert annotations[0].type[1] == "Highlight"
    assert annotations[0].colors["stroke"] == pytest.approx(GREEN)
    document.close()
