from collections.abc import Mapping
from typing import Any

import fitz  # type: ignore[import-untyped]

from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.models.annotation_item import AnnotationItem
from contract_diff.models.document.bounding_box import BoundingBox
from contract_diff.rendering.styles.pdf_colors import style_for_annotation_type


class MarkerRenderer:
    """
    Deletion marker renderer.
    """

    def render(
        self,
        pdf_document: Any,
        annotation: AnnotationItem,
        span_boxes: Mapping[str, BoundingBox],
    ) -> tuple[str, ...]:
        if annotation.annotation_type is not AnnotationType.REMOVED:
            return ()

        if annotation.target is None:
            return (f"{annotation.id}:SKIPPED_MARKER_WITHOUT_TARGET",)

        page = self._page(pdf_document, annotation.target.page_number)

        if page is None:
            return (f"{annotation.id}:MISSING_RENDER_TARGET_PAGE",)

        bbox, warnings = self._first_bbox(annotation, span_boxes)

        if bbox is None:
            return warnings

        # TODO(v2): Replace deletion margin markers with sidebar deletion callouts.
        marker = page.add_underline_annot(self._margin_marker_rect(bbox))
        style = style_for_annotation_type(annotation.annotation_type)
        marker.set_colors(stroke=style.color)
        marker.set_opacity(style.opacity)
        marker.set_info(
            title=annotation.id,
            content=self._annotation_content(annotation),
        )
        marker.update()
        return warnings

    def _page(self, pdf_document: Any, page_number: int) -> Any | None:
        if page_number < 1 or page_number > pdf_document.page_count:
            return None

        return pdf_document[page_number - 1]

    def _first_bbox(
        self,
        annotation: AnnotationItem,
        span_boxes: Mapping[str, BoundingBox],
    ) -> tuple[BoundingBox | None, tuple[str, ...]]:
        if annotation.target is None:
            return None, (f"{annotation.id}:SKIPPED_MARKER_WITHOUT_TARGET",)

        warnings: list[str] = []

        for span_id in annotation.target.source_span_ids:
            bbox = span_boxes.get(span_id)

            if bbox is not None:
                return bbox, tuple(warnings)

            warnings.append(f"{annotation.id}:MISSING_SPAN:{span_id}")

        return None, tuple(warnings)

    def _margin_marker_rect(self, bbox: BoundingBox) -> fitz.Rect:
        y0 = max(0.0, bbox.y0 + 2.0)
        y1 = y0 + 5.0
        return fitz.Rect(24.0, y0, 44.0, y1)

    def _annotation_content(self, annotation: AnnotationItem) -> str:
        summary = annotation.original_text or annotation.revised_text or ""
        summary = " ".join(summary.split())

        if len(summary) > 140:
            summary = f"{summary[:137]}..."

        return f"Deleted: {summary}" if summary else "Deleted"
