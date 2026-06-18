from __future__ import annotations

import sys
from pathlib import Path

import fitz

from contract_diff.rendering.utils.visual_diagnostics import (
    collect_visual_diagnostics,
)

UNWANTED_ANNOTATION_TYPES = {"Square", "Text", "FreeText", "Rect"}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: diagnose_visuals.py ANNOTATED.pdf")
        return 2

    pdf_path = Path(sys.argv[1])

    with fitz.open(pdf_path) as document:
        diagnostics = collect_visual_diagnostics(document)
        annotation_counts = diagnostics.annotation_counts

        print("total highlights:", diagnostics.total_highlights)
        print(
            "highlight annotations by page:",
            diagnostics.highlight_annotations_by_page,
        )
        print("text annotations:", annotation_counts.get("Text", 0))
        print("square annotations:", annotation_counts.get("Square", 0))
        print("freetext annotations:", annotation_counts.get("FreeText", 0))
        print("rect annotations:", annotation_counts.get("Rect", 0))
        print(
            "max highlights on one page:",
            diagnostics.max_highlights_on_one_page,
        )
        print(
            "estimated highlighted area per page:",
            {
                page_number: round(area_ratio, 4)
                for page_number, area_ratio in (
                    diagnostics.highlighted_area_ratio_by_page.items()
                )
            },
        )
        print("pages with dense highlights:", diagnostics.dense_pages)

        unwanted_count = sum(
            annotation_counts.get(annotation_type, 0)
            for annotation_type in UNWANTED_ANNOTATION_TYPES
        )

        if unwanted_count:
            print("WARNING: output contains Square/Text/FreeText/Rect annotations")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
