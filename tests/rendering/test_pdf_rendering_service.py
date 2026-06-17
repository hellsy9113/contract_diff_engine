import fitz  # type: ignore[import-untyped]

from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.enums.highlight_style import HighlightStyle
from contract_diff.annotation.models.annotation_plan import (
    AnnotationPlan,
    AnnotationSummary,
)
from contract_diff.rendering.services.pdf_rendering_service import PdfRenderingService
from tests.rendering.helpers import (
    make_annotation,
    make_annotation_plan,
    make_extracted_document,
    make_pdf_bytes,
)


def test_renderer_returns_openable_pdf_bytes_with_appendix_page() -> None:
    annotation = make_annotation(
        AnnotationType.MODIFIED,
        HighlightStyle.MODIFIED_HIGHLIGHT,
    )
    plan = make_annotation_plan((annotation,))

    rendered = PdfRenderingService().render(
        make_pdf_bytes(),
        make_extracted_document(),
        plan,
    )

    document = fitz.open(stream=rendered.data, filetype="pdf")
    assert rendered.filename == "revised-annotated.pdf"
    assert rendered.content_type == "application/pdf"
    assert rendered.warnings == ()
    assert document.page_count == 2
    page = document[0]
    assert list(page.annots() or [])
    assert "Annotation ANN-1" in document[1].get_text()
    document.close()


def test_unchanged_is_ignored_by_empty_annotation_plan() -> None:
    plan = AnnotationPlan(
        annotations=(),
        appendix_entries=(),
        summary=AnnotationSummary(
            total=0,
            modified=0,
            added=0,
            removed=0,
            unresolved=0,
        ),
    )

    rendered = PdfRenderingService().render(
        make_pdf_bytes(),
        make_extracted_document(),
        plan,
    )

    document = fitz.open(stream=rendered.data, filetype="pdf")
    assert document.page_count == 1
    page = document[0]
    assert list(page.annots() or []) == []
    document.close()


def test_missing_span_ids_produce_warnings_not_crash() -> None:
    annotation = make_annotation(
        AnnotationType.MODIFIED,
        HighlightStyle.MODIFIED_HIGHLIGHT,
        span_ids=("missing-span",),
    )
    plan = make_annotation_plan((annotation,))

    rendered = PdfRenderingService().render(
        make_pdf_bytes(),
        make_extracted_document(),
        plan,
    )

    document = fitz.open(stream=rendered.data, filetype="pdf")
    assert "ANN-1:MISSING_SPAN:missing-span" in rendered.warnings
    assert document.page_count == 2
    document.close()
