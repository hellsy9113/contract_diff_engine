from collections.abc import Mapping
from typing import Any

import fitz  # type: ignore[import-untyped]

from contract_diff.annotation.models.annotation_item import AnnotationItem
from contract_diff.models.document.bounding_box import BoundingBox


class PopupRenderer:
    """
    Adds popup/comment annotations near the first target span.
    """

    def render(
        self,
        pdf_document: Any,
        annotation: AnnotationItem,
        span_boxes: Mapping[str, BoundingBox],
    ) -> tuple[str, ...]:
        if annotation.target is None:
            return (f"{annotation.id}:SKIPPED_POPUP_WITHOUT_TARGET",)

        page = self._page(pdf_document, annotation.target.page_number)

        if page is None:
            return (f"{annotation.id}:MISSING_RENDER_TARGET_PAGE",)

        bbox, warnings = self._first_bbox(annotation, span_boxes)

        if bbox is None:
            return warnings

        popup = page.add_text_annot(
            fitz.Point(bbox.x1 + 4.0, bbox.y0),
            annotation.popup_text,
        )
        popup.set_info(title=annotation.id, content=annotation.popup_text)
        popup.update()

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
            return None, (f"{annotation.id}:SKIPPED_POPUP_WITHOUT_TARGET",)

        warnings: list[str] = []

        for span_id in annotation.target.source_span_ids:
            bbox = span_boxes.get(span_id)

            if bbox is not None:
                return bbox, tuple(warnings)

            warnings.append(f"{annotation.id}:MISSING_SPAN:{span_id}")

        return None, tuple(warnings)
