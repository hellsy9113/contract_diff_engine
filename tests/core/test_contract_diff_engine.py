import fitz  # type: ignore[import-untyped]

from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.enums.highlight_style import HighlightStyle
from contract_diff.annotation.models.annotation_appendix_entry import (
    AnnotationAppendixEntry,
)
from contract_diff.annotation.models.annotation_item import AnnotationItem
from contract_diff.annotation.models.annotation_plan import (
    AnnotationPlan,
    AnnotationSummary,
)
from contract_diff.annotation.models.annotation_target import AnnotationTarget
from contract_diff.annotation.services.annotation_builder_service import (
    AnnotationBuilderService,
)
from contract_diff.comparison.models.comparison_result import ComparisonResult
from contract_diff.core.models.engine_status import EngineStatus
from contract_diff.core.services.contract_diff_engine import ContractDiffEngine


def make_pdf(lines: tuple[str, ...]) -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)

    for index, line in enumerate(lines):
        page.insert_text((72, 90 + (index * 42)), line, fontsize=12)

    pdf_bytes = document.tobytes()
    document.close()
    return bytes(pdf_bytes)


def similar_original_pdf() -> bytes:
    return make_pdf(
        (
            "1. Payment Terms",
            "1.1 Payment shall be made within 30 days.",
            "1.2 Supplier shall maintain insurance.",
        )
    )


def similar_revised_pdf() -> bytes:
    return make_pdf(
        (
            "1. Payment Terms",
            "1.1 Payment shall be made within 45 days.",
            "1.2 Supplier shall maintain insurance.",
        )
    )


def unrelated_pdf() -> bytes:
    return make_pdf(
        (
            "1. Software License",
            "1.1 Licensee may install the application on one computer.",
            "1.2 Source code escrow is prohibited unless approved.",
        )
    )


class MissingSpanAnnotationBuilder(AnnotationBuilderService):
    def build(self, comparison_result: ComparisonResult) -> AnnotationPlan:
        annotation = AnnotationItem(
            id="ANN-1",
            annotation_type=AnnotationType.ADDED,
            style=HighlightStyle.ADDED_HIGHLIGHT,
            target=AnnotationTarget(
                clause_id="clause-1",
                page_number=1,
                source_span_ids=("missing-span",),
                anchor_type="revised_clause",
            ),
            original_text="Payment shall be made within 30 days.",
            revised_text=None,
            popup_text="Payment shall be made within 30 days.",
            heading="Payment Terms",
            page_number=1,
        )

        return AnnotationPlan(
            annotations=(annotation,),
            appendix_entries=(
                AnnotationAppendixEntry(
                    annotation_id=annotation.id,
                    annotation_type=annotation.annotation_type,
                    page_number=annotation.page_number,
                    heading=annotation.heading,
                    original_text=annotation.original_text,
                    revised_text=annotation.revised_text,
                ),
            ),
            summary=AnnotationSummary(
                total=1,
                modified=0,
                added=1,
                removed=0,
                unresolved=0,
            ),
        )


def test_similar_pdfs_return_success_with_pdf_bytes() -> None:
    result = ContractDiffEngine().compare(
        similar_original_pdf(),
        similar_revised_pdf(),
    )

    assert result.status is EngineStatus.SUCCESS
    assert result.rendered_document is not None
    assert result.rendered_document.content_type == "application/pdf"
    assert result.rendered_document.data.startswith(b"%PDF")


def test_successful_rendered_pdf_can_be_opened() -> None:
    result = ContractDiffEngine().compare(
        similar_original_pdf(),
        similar_revised_pdf(),
    )

    assert result.rendered_document is not None
    document = fitz.open(stream=result.rendered_document.data, filetype="pdf")
    assert document.page_count == 1
    page = document[0]
    assert list(page.annots() or [])
    document.close()


def test_low_similarity_returns_rejected_without_pdf_bytes() -> None:
    result = ContractDiffEngine().compare(
        similar_original_pdf(),
        unrelated_pdf(),
    )

    assert result.status is EngineStatus.REJECTED
    assert result.rendered_document is None
    assert result.rejection_reason == "LOW_DOCUMENT_SIMILARITY"
    assert result.similarity_score is not None
    assert result.similarity_score < 50
    assert result.message is not None
    assert "less than 50% similar" in result.message


def test_pipeline_preserves_warnings() -> None:
    original = make_pdf(("1.1 Payment shall be made within 30 days.",))
    revised = make_pdf(("1.1 Payment shall be made within 45 days.",))

    result = ContractDiffEngine().compare(original, revised)

    assert result.status is EngineStatus.SUCCESS
    assert "Clause clause-1 is not attached to a section." in result.warnings
    assert result.rendered_document is not None
    assert result.rendered_document.warnings == result.warnings


def test_engine_does_not_crash_on_missing_annotations() -> None:
    engine = ContractDiffEngine(
        annotation_builder_service=MissingSpanAnnotationBuilder(),
    )

    result = engine.compare(similar_original_pdf(), similar_revised_pdf())

    assert result.status is EngineStatus.SUCCESS
    assert result.rendered_document is not None
    assert "ANN-1:MISSING_SPAN:missing-span" in result.warnings


def test_unnumbered_pdf_text_changes_use_line_level_fallback() -> None:
    original = make_pdf(
        (
            "Introduction",
            "Quantum search is discussed.",
        )
    )
    revised = make_pdf(
        (
            "Introduction",
            "Quantum search is discussed.",
            "Grover's algorithm speeds unstructured search.",
        )
    )

    result = ContractDiffEngine().compare(original, revised)

    assert result.status is EngineStatus.SUCCESS
    assert result.rendered_document is not None
    assert "LINE_LEVEL_FALLBACK_COMPARISON" in result.warnings

    document = fitz.open(stream=result.rendered_document.data, filetype="pdf")
    page = document[0]
    annotations = list(page.annots() or [])

    assert annotations
    assert document.page_count == 1
    document.close()


def test_output_uses_revised_pdf_as_visual_base() -> None:
    original = make_pdf(
        ("Shor's algorithm affects public key cryptography.",)
    )
    revised = make_pdf(
        (
            "Shor's algorithm affects public key cryptography. "
            "Grover's algorithm also impacts symmetric security.",
        )
    )

    result = ContractDiffEngine().compare(original, revised)

    assert result.status is EngineStatus.SUCCESS
    assert result.rendered_document is not None

    document = fitz.open(stream=result.rendered_document.data, filetype="pdf")
    assert "Grover's algorithm" in document[0].get_text()
    document.close()


def test_output_has_no_square_text_or_freetext_annotations() -> None:
    result = ContractDiffEngine().compare(
        similar_original_pdf(),
        similar_revised_pdf(),
    )

    assert result.status is EngineStatus.SUCCESS
    assert result.rendered_document is not None

    document = fitz.open(stream=result.rendered_document.data, filetype="pdf")
    unwanted_types = {"Text", "Square", "FreeText"}

    for page in document:
        annotation = page.first_annot

        while annotation is not None:
            assert annotation.type[1] not in unwanted_types
            annotation = annotation.next

    document.close()
