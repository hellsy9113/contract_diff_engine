from collections.abc import Mapping
from typing import Any

import fitz  # type: ignore[import-untyped]

from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.models.annotation_item import AnnotationItem
from contract_diff.models.document.bounding_box import BoundingBox
from contract_diff.rendering.styles.pdf_colors import RED


class MarkerRenderer:
    """
    Draws red deletion markers near revised anchor clauses.
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

        marker = page.add_rect_annot(self._marker_rect(page, bbox))
        marker.set_colors(stroke=RED, fill=RED)
        marker.set_info(title=annotation.id, content=annotation.popup_text)
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

    def _marker_rect(self, page: Any, bbox: BoundingBox) -> fitz.Rect:
        x1 = max(4.0, bbox.x0 - 6.0)
        x0 = max(0.0, x1 - 8.0)
        y0 = max(0.0, bbox.y0)
        y1 = min(float(page.rect.height), y0 + 12.0)
        return fitz.Rect(x0, y0, x1, y1)
