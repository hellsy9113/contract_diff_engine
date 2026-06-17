from collections.abc import Mapping
from typing import Any

import fitz  # type: ignore[import-untyped]

from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.models.annotation_item import AnnotationItem
from contract_diff.models.document.bounding_box import BoundingBox
from contract_diff.rendering.styles.pdf_colors import color_for_style


class HighlightRenderer:
    """
    Draws clause-level highlight annotations for added and modified clauses.
    """

    def render(
        self,
        pdf_document: Any,
        annotation: AnnotationItem,
        span_boxes: Mapping[str, BoundingBox],
    ) -> tuple[str, ...]:
        if annotation.annotation_type not in {
            AnnotationType.MODIFIED,
            AnnotationType.ADDED,
        }:
            return ()

        if annotation.target is None:
            return (f"{annotation.id}:SKIPPED_HIGHLIGHT_WITHOUT_TARGET",)

        page = self._page(pdf_document, annotation.target.page_number)

        if page is None:
            return (f"{annotation.id}:MISSING_RENDER_TARGET_PAGE",)

        warnings: list[str] = []
        color = color_for_style(annotation.style)

        for span_id in annotation.target.source_span_ids:
            bbox = span_boxes.get(span_id)

            if bbox is None:
                warnings.append(f"{annotation.id}:MISSING_SPAN:{span_id}")
                continue

            highlight = page.add_highlight_annot(self._rect(bbox))
            highlight.set_colors(stroke=color)
            highlight.set_info(title=annotation.id, content=annotation.popup_text)
            highlight.update()

        return tuple(warnings)

    def _page(self, pdf_document: Any, page_number: int) -> Any | None:
        if page_number < 1 or page_number > pdf_document.page_count:
            return None

        return pdf_document[page_number - 1]

    def _rect(self, bbox: BoundingBox) -> fitz.Rect:
        return fitz.Rect(bbox.x0, bbox.y0, bbox.x1, bbox.y1)
