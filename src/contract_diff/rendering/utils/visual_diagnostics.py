from __future__ import annotations

import logging
from dataclasses import dataclass

import fitz  # type: ignore[import-untyped]

from contract_diff.rendering.styles.pdf_colors import (
    MAX_HIGHLIGHTED_AREA_RATIO_PER_PAGE,
)
from contract_diff.rendering.utils.pdf_rects import rect_area

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PageVisualDiagnostics:
    page_number: int
    highlight_count: int
    highlighted_area_ratio: float


@dataclass(frozen=True)
class PdfVisualDiagnostics:
    annotation_counts: dict[str, int]
    highlight_annotations_by_page: dict[int, int]
    highlighted_area_ratio_by_page: dict[int, float]
    dense_pages: tuple[int, ...]

    @property
    def total_highlights(self) -> int:
        return self.annotation_counts.get("Highlight", 0)

    @property
    def max_highlights_on_one_page(self) -> int:
        if not self.highlight_annotations_by_page:
            return 0

        return max(self.highlight_annotations_by_page.values())


def collect_visual_diagnostics(
    document: fitz.Document,
    dense_area_threshold: float = MAX_HIGHLIGHTED_AREA_RATIO_PER_PAGE,
) -> PdfVisualDiagnostics:
    annotation_counts: dict[str, int] = {}
    highlight_annotations_by_page: dict[int, int] = {}
    highlighted_area_ratio_by_page: dict[int, float] = {}
    dense_pages: list[int] = []

    for page_index, page in enumerate(document):
        page_number = page_index + 1
        page_area = max(1.0, float(page.rect.width) * float(page.rect.height))
        highlighted_area = 0.0
        highlight_count = 0
        annotation = page.first_annot

        while annotation is not None:
            annotation_type = annotation.type[1]
            annotation_counts[annotation_type] = (
                annotation_counts.get(annotation_type, 0) + 1
            )

            if annotation_type == "Highlight":
                highlight_count += 1
                highlighted_area += rect_area(annotation.rect)

            annotation = annotation.next

        if highlight_count:
            highlight_annotations_by_page[page_number] = highlight_count
            area_ratio = highlighted_area / page_area
            highlighted_area_ratio_by_page[page_number] = area_ratio

            if area_ratio > dense_area_threshold:
                dense_pages.append(page_number)

    return PdfVisualDiagnostics(
        annotation_counts=annotation_counts,
        highlight_annotations_by_page=highlight_annotations_by_page,
        highlighted_area_ratio_by_page=highlighted_area_ratio_by_page,
        dense_pages=tuple(dense_pages),
    )


def print_dense_page_warnings(
    diagnostics: PdfVisualDiagnostics,
) -> None:
    for page_number in diagnostics.dense_pages:
        logger.warning(
            "page %s has dense highlights; consider fragment filtering",
            page_number,
        )
