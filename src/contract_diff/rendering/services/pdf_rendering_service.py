from io import BytesIO
from typing import BinaryIO

import fitz  # type: ignore[import-untyped]

from contract_diff.annotation.models.annotation_plan import AnnotationPlan
from contract_diff.models.document.bounding_box import BoundingBox
from contract_diff.models.document.extracted_document import ExtractedDocument
from contract_diff.rendering.models.rendered_document import RenderedDocument
from contract_diff.rendering.services.appendix_renderer import AppendixRenderer
from contract_diff.rendering.services.highlight_renderer import HighlightRenderer
from contract_diff.rendering.services.marker_renderer import MarkerRenderer
from contract_diff.rendering.services.popup_renderer import PopupRenderer
from contract_diff.rendering.utils.visual_diagnostics import (
    collect_visual_diagnostics,
    print_dense_page_warnings,
)


class PdfRenderingService:
    """
    Renders an annotation plan into revised PDF bytes.
    """

    def __init__(
        self,
        highlight_renderer: HighlightRenderer | None = None,
        marker_renderer: MarkerRenderer | None = None,
        popup_renderer: PopupRenderer | None = None,
        appendix_renderer: AppendixRenderer | None = None,
    ) -> None:
        self._highlight_renderer = highlight_renderer or HighlightRenderer()
        self._marker_renderer = marker_renderer or MarkerRenderer()
        self._popup_renderer = popup_renderer or PopupRenderer()
        self._appendix_renderer = appendix_renderer or AppendixRenderer()

    def render(
        self,
        revised_pdf_stream: bytes | BinaryIO,
        extracted_revised_document: ExtractedDocument,
        annotation_plan: AnnotationPlan,
    ) -> RenderedDocument:
        pdf_bytes = self._read_pdf_bytes(revised_pdf_stream)
        span_boxes = self._span_boxes(extracted_revised_document)
        warnings: list[str] = list(annotation_plan.warnings)

        with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf_document:
            for annotation in annotation_plan.annotations:
                warnings.extend(
                    self._highlight_renderer.render(
                        pdf_document,
                        annotation,
                        span_boxes,
                    )
                )
                warnings.extend(
                    self._marker_renderer.render(
                        pdf_document,
                        annotation,
                        span_boxes,
                    )
                )
                # TODO(v2): Reintroduce richer deletion callouts/sidebar after
                # non-overlapping layout is implemented.
                # self._popup_renderer.render(pdf_document, annotation, span_boxes)

            visual_diagnostics = collect_visual_diagnostics(pdf_document)
            print_dense_page_warnings(visual_diagnostics)
            warnings.extend(
                f"DENSE_HIGHLIGHTS_PAGE:{page_number}"
                for page_number in visual_diagnostics.dense_pages
            )

            # TODO(v2): Re-enable appendix generation after compact appendix
            # layout is implemented.
            # self._appendix_renderer.render(pdf_document, annotation_plan)
            output = BytesIO()
            pdf_document.save(output, garbage=4, deflate=True)
            rendered_bytes = output.getvalue()

        return RenderedDocument(
            filename=self._rendered_filename(extracted_revised_document),
            data=rendered_bytes,
            warnings=self._unique(tuple(warnings)),
        )

    def _read_pdf_bytes(self, revised_pdf_stream: bytes | BinaryIO) -> bytes:
        if isinstance(revised_pdf_stream, bytes):
            return revised_pdf_stream

        position = revised_pdf_stream.tell()

        try:
            revised_pdf_stream.seek(0)
            return revised_pdf_stream.read()

        finally:
            revised_pdf_stream.seek(position)

    def _span_boxes(
        self,
        extracted_document: ExtractedDocument,
    ) -> dict[str, BoundingBox]:
        span_boxes: dict[str, BoundingBox] = {}

        for page in extracted_document.pages:
            for block in page.blocks:
                for line in block.lines:
                    for span in line.spans:
                        if span.bbox is None:
                            continue

                        span_boxes[span.id] = span.bbox

        return span_boxes

    def _rendered_filename(self, extracted_document: ExtractedDocument) -> str:
        stem = extracted_document.metadata.stem
        return f"{stem}-annotated.pdf"

    def _unique(self, warnings: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        unique_warnings: list[str] = []

        for warning in warnings:
            if warning in seen:
                continue

            seen.add(warning)
            unique_warnings.append(warning)

        return tuple(unique_warnings)
