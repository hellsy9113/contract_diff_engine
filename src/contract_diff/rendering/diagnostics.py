from __future__ import annotations

from typing import Any, cast

import fitz  # type: ignore[import-untyped]

from contract_diff.rendering.styles.pdf_colors import (
    MAX_HIGHLIGHTED_AREA_RATIO_PER_PAGE,
)
from contract_diff.rendering.styles.v2 import MAX_HIGHLIGHTS_PER_PAGE
from contract_diff.rendering.utils.pdf_rects import rect_area

UNWANTED_ANNOTATION_TYPES = frozenset({"Text", "Square", "FreeText", "Rect"})


def analyze_rendered_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """Return annotation diagnostics for a rendered PDF."""

    document = fitz.open(stream=pdf_bytes, filetype="pdf")

    try:
        annotation_counts: dict[str, int] = {}
        highlights_by_page: dict[int, int] = {}
        dense_pages: list[int] = []
        unwanted_annotation_count = 0

        for page_index, page in enumerate(document):
            page_number = page_index + 1
            page_area = max(1.0, float(page.rect.width) * float(page.rect.height))
            highlighted_area = 0.0
            highlight_count = 0
            annotation = page.first_annot

            while annotation is not None:
                annotation_type = cast(str, annotation.type[1])
                annotation_counts[annotation_type] = (
                    annotation_counts.get(annotation_type, 0) + 1
                )

                if annotation_type in UNWANTED_ANNOTATION_TYPES:
                    unwanted_annotation_count += 1

                if annotation_type == "Highlight":
                    highlight_count += 1
                    highlighted_area += rect_area(annotation.rect)

                annotation = annotation.next

            if highlight_count:
                highlights_by_page[page_number] = highlight_count

            if _is_dense_page(highlight_count, highlighted_area, page_area):
                dense_pages.append(page_number)

        return {
            "annotation_counts": annotation_counts,
            "highlights_by_page": highlights_by_page,
            "unwanted_annotation_count": unwanted_annotation_count,
            "dense_pages": dense_pages,
            "max_highlights_on_page": max(highlights_by_page.values(), default=0),
        }
    finally:
        document.close()


def _is_dense_page(
    highlight_count: int,
    highlighted_area: float,
    page_area: float,
) -> bool:
    if highlight_count > MAX_HIGHLIGHTS_PER_PAGE:
        return True

    if not highlight_count:
        return False

    return highlighted_area / page_area > MAX_HIGHLIGHTED_AREA_RATIO_PER_PAGE
