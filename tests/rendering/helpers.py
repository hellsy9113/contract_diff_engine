from collections.abc import Sequence
from typing import cast

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
from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.models.document.block import Block
from contract_diff.models.document.bounding_box import BoundingBox
from contract_diff.models.document.extracted_document import ExtractedDocument
from contract_diff.models.document.line import Line
from contract_diff.models.document.metadata import DocumentMetadata
from contract_diff.models.document.page import Page
from contract_diff.models.document.span import Span


def make_pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 90), "Payment shall be made within 45 days.")
    pdf_bytes = cast(bytes, document.tobytes())
    document.close()
    return pdf_bytes


def make_span_box() -> BoundingBox:
    return BoundingBox(x0=72, y0=76, x1=260, y1=96)


def make_annotation(
    annotation_type: AnnotationType,
    style: HighlightStyle,
    annotation_id: str = "ANN-1",
    span_ids: tuple[str, ...] = ("span-rev-1",),
    target: AnnotationTarget | None = None,
) -> AnnotationItem:
    if target is None:
        target = AnnotationTarget(
            clause_id="rev-1",
            page_number=1,
            source_span_ids=span_ids,
            anchor_type="revised_clause"
            if annotation_type is not AnnotationType.REMOVED
            else "revised_anchor_clause",
        )

    return AnnotationItem(
        id=annotation_id,
        annotation_type=annotation_type,
        style=style,
        target=target,
        original_text="Payment shall be made within 30 days.",
        revised_text="Payment shall be made within 45 days.",
        popup_text="Payment shall be made within 30 days.",
        heading="Payment Terms",
        page_number=1,
    )


def make_annotation_plan(
    annotations: Sequence[AnnotationItem],
) -> AnnotationPlan:
    appendix_entries = tuple(
        AnnotationAppendixEntry(
            annotation_id=annotation.id,
            annotation_type=annotation.annotation_type,
            page_number=annotation.page_number,
            heading=annotation.heading,
            original_text=annotation.original_text,
            revised_text=annotation.revised_text,
            notes=annotation.warnings,
        )
        for annotation in annotations
    )

    return AnnotationPlan(
        annotations=tuple(annotations),
        appendix_entries=appendix_entries,
        summary=AnnotationSummary(
            total=len(annotations),
            modified=sum(
                1
                for annotation in annotations
                if annotation.annotation_type is AnnotationType.MODIFIED
            ),
            added=sum(
                1
                for annotation in annotations
                if annotation.annotation_type is AnnotationType.ADDED
            ),
            removed=sum(
                1
                for annotation in annotations
                if annotation.annotation_type is AnnotationType.REMOVED
            ),
            unresolved=sum(
                1 for annotation in annotations if annotation.target is None
            ),
        ),
    )


def make_extracted_document(
    span_id: str = "span-rev-1",
    bbox: BoundingBox | None = None,
) -> ExtractedDocument:
    if bbox is None:
        bbox = make_span_box()

    return ExtractedDocument(
        format=DocumentFormat.PDF,
        metadata=DocumentMetadata(
            filename="revised.pdf",
            extension=".pdf",
            size_bytes=100,
            page_count=1,
        ),
        pages=(
            Page(
                id="page-1",
                page_number=1,
                bbox=BoundingBox(x0=0, y0=0, x1=595, y1=842),
                blocks=(
                    Block(
                        id="block-1",
                        bbox=bbox,
                        lines=(
                            Line(
                                id="line-1",
                                bbox=bbox,
                                spans=(
                                    Span(
                                        id=span_id,
                                        text="Payment shall be made within 45 days.",
                                        bbox=bbox,
                                        font="Helvetica",
                                        font_size=12,
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
