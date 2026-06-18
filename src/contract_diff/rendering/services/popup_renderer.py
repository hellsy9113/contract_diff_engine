from collections.abc import Mapping
from typing import Any

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
        _ = (pdf_document, annotation, span_boxes)
        # TODO(v2): Reintroduce richer deletion callouts/sidebar after
        # non-overlapping layout is implemented.
        return ()
