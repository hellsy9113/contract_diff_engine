import fitz  # type: ignore[import-untyped]

from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.enums.highlight_style import HighlightStyle
from contract_diff.annotation.models.annotation_plan import (
    AnnotationPlan,
    AnnotationSummary,
)
from contract_diff.comparison.enums.fragment_operation import FragmentOperation
from contract_diff.comparison.models.text_fragment import TextFragment
from contract_diff.rendering.services.pdf_rendering_service import PdfRenderingService
from tests.rendering.helpers import (
    make_annotation,
    make_annotation_plan,
    make_extracted_document,
    make_pdf_bytes,
)


def test_renderer_returns_openable_pdf_bytes_without_appendix_page() -> None:
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
    assert document.page_count == 1
    page = document[0]
    assert list(page.annots() or [])
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
        AnnotationType.ADDED,
        HighlightStyle.ADDED_HIGHLIGHT,
        span_ids=("missing-span",),
    ).model_copy(
        update={"revised_text": None}
    )
    plan = make_annotation_plan((annotation,))

    rendered = PdfRenderingService().render(
        make_pdf_bytes(),
        make_extracted_document(),
        plan,
    )

    document = fitz.open(stream=rendered.data, filetype="pdf")
    assert "ANN-1:MISSING_SPAN:missing-span" in rendered.warnings
    assert document.page_count == 1
    document.close()


def test_rendered_pdf_uses_allowed_visual_annotation_types_only() -> None:
    annotations = (
        make_annotation(
            AnnotationType.MODIFIED,
            HighlightStyle.MODIFIED_HIGHLIGHT,
        ),
        make_annotation(
            AnnotationType.ADDED,
            HighlightStyle.ADDED_HIGHLIGHT,
            annotation_id="ANN-2",
        ),
        make_annotation(
            AnnotationType.REMOVED,
            HighlightStyle.REMOVED_MARKER,
            annotation_id="ANN-3",
        ),
    )
    plan = make_annotation_plan(annotations)

    rendered = PdfRenderingService().render(
        make_pdf_bytes(),
        make_extracted_document(),
        plan,
    )

    document = fitz.open(stream=rendered.data, filetype="pdf")
    annotation_types = _annotation_types(document)

    assert annotation_types
    assert annotation_types <= {"Highlight", "Underline", "StrikeOut"}
    assert annotation_types.isdisjoint({"Text", "Square", "FreeText", "Rect"})
    document.close()


def test_duplicate_visual_fragments_do_not_duplicate_highlight_rects() -> None:
    annotation = make_annotation(
        AnnotationType.MODIFIED,
        HighlightStyle.MODIFIED_HIGHLIGHT,
    ).model_copy(
        update={
            "fragments": (
                TextFragment(
                    operation=FragmentOperation.INSERTED,
                    sequence_index=1,
                    revised_text="45",
                ),
                TextFragment(
                    operation=FragmentOperation.INSERTED,
                    sequence_index=2,
                    revised_text="45",
                ),
            )
        }
    )
    plan = make_annotation_plan((annotation,))

    rendered = PdfRenderingService().render(
        make_pdf_bytes(),
        make_extracted_document(),
        plan,
    )

    document = fitz.open(stream=rendered.data, filetype="pdf")

    assert _annotation_type_counts(document) == {"Highlight": 1}
    document.close()


def _annotation_types(document: fitz.Document) -> set[str]:
    annotation_types: set[str] = set()

    for page in document:
        annotation = page.first_annot

        while annotation is not None:
            annotation_types.add(annotation.type[1])
            annotation = annotation.next

    return annotation_types


def _annotation_type_counts(document: fitz.Document) -> dict[str, int]:
    annotation_type_counts: dict[str, int] = {}

    for page in document:
        annotation = page.first_annot

        while annotation is not None:
            annotation_type = annotation.type[1]
            annotation_type_counts[annotation_type] = (
                annotation_type_counts.get(annotation_type, 0) + 1
            )
            annotation = annotation.next

    return annotation_type_counts
