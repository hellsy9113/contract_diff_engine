import fitz  # type: ignore[import-untyped]
import pytest

from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.enums.highlight_style import HighlightStyle
from contract_diff.rendering.services.marker_renderer import MarkerRenderer
from contract_diff.rendering.styles.pdf_colors import RED
from tests.rendering.helpers import make_annotation, make_pdf_bytes, make_span_box


def test_removed_annotation_creates_red_marker() -> None:
    document = fitz.open(stream=make_pdf_bytes(), filetype="pdf")
    annotation = make_annotation(
        AnnotationType.REMOVED,
        HighlightStyle.REMOVED_MARKER,
    )

    warnings = MarkerRenderer().render(
        document,
        annotation,
        {"span-rev-1": make_span_box()},
    )

    page = document[0]
    annotations = list(page.annots() or [])
    assert warnings == ()
    assert annotations[0].type[1] == "Square"
    assert annotations[0].colors["stroke"] == pytest.approx(RED)
    document.close()
