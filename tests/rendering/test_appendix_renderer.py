import fitz  # type: ignore[import-untyped]

from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.enums.highlight_style import HighlightStyle
from contract_diff.rendering.services.appendix_renderer import AppendixRenderer
from tests.rendering.helpers import (
    make_annotation,
    make_annotation_plan,
    make_pdf_bytes,
)


def test_appendix_page_is_added() -> None:
    document = fitz.open(stream=make_pdf_bytes(), filetype="pdf")
    annotation = make_annotation(
        AnnotationType.MODIFIED,
        HighlightStyle.MODIFIED_HIGHLIGHT,
    )
    plan = make_annotation_plan((annotation,))

    AppendixRenderer().render(document, plan)

    assert document.page_count == 2
    assert "Annotation ANN-1" in document[1].get_text()
    assert "Payment Terms" in document[1].get_text()
    document.close()
