from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import fitz

from contract_diff.comparison.services.text_unit_comparison_service import (
    TextUnitComparisonService,
)
from contract_diff.core.models.engine_status import EngineStatus
from contract_diff.core.services.contract_diff_engine import ContractDiffEngine
from contract_diff.extraction.readers.pdf.pdf_reader import PdfReader
from contract_diff.normalization.services.normalization_service import (
    NormalizationService,
)
from contract_diff.rendering.utils.visual_diagnostics import (
    collect_visual_diagnostics,
)

UNWANTED_ANNOTATION_TYPES = {"Square", "Text", "FreeText", "Rect"}


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: diagnose_compare.py ORIGINAL.pdf REVISED.pdf")
        return 2

    original_path = Path(sys.argv[1])
    revised_path = Path(sys.argv[2])
    original_bytes = original_path.read_bytes()
    revised_bytes = revised_path.read_bytes()
    reader = PdfReader()
    normalizer = NormalizationService()

    original_extracted = reader.extract(BytesIO(original_bytes), original_path.name)
    revised_extracted = reader.extract(BytesIO(revised_bytes), revised_path.name)
    original_normalized = normalizer.normalize(original_extracted)
    revised_normalized = normalizer.normalize(revised_extracted)
    text_unit_comparison = TextUnitComparisonService().compare(
        original_normalized,
        revised_normalized,
    )

    result = ContractDiffEngine().compare(
        original_bytes,
        revised_bytes,
        original_filename=original_path.name,
        revised_filename=revised_path.name,
    )

    print("original bytes:", len(original_bytes))
    print("revised bytes:", len(revised_bytes))
    print("output base: revised")
    print("original pages:", len(original_extracted.pages))
    print("revised pages:", len(revised_extracted.pages))
    print("original text chars:", len(original_extracted.text))
    print("revised text chars:", len(revised_extracted.text))
    print("texts equal:", original_extracted.text == revised_extracted.text)
    print("original blocks:", _unit_count(original_normalized))
    print("revised blocks:", _unit_count(revised_normalized))

    if result.status is not EngineStatus.SUCCESS or result.rendered_document is None:
        print("engine status:", result.status.value)
        print("message:", result.message)
        print("warnings:", result.warnings)
        return 1

    output_bytes = result.rendered_document.data
    output_document = fitz.open(stream=output_bytes, filetype="pdf")
    diagnostics = collect_visual_diagnostics(output_document)
    annotation_counts = diagnostics.annotation_counts
    output_text = "\n".join(page.get_text() for page in output_document)

    print("output pages:", output_document.page_count)
    print("output text chars:", len(output_text))
    print("insertions:", text_unit_comparison.summary.added)
    print("deletions:", text_unit_comparison.summary.removed)
    print("modifications:", text_unit_comparison.summary.modified)
    print("total highlights:", diagnostics.total_highlights)
    print(
        "highlight annotations by page:",
        diagnostics.highlight_annotations_by_page,
    )
    print("square annotations:", annotation_counts.get("Square", 0))
    print("text annotations:", annotation_counts.get("Text", 0))
    print("freetext annotations:", annotation_counts.get("FreeText", 0))
    print("rect annotations:", annotation_counts.get("Rect", 0))
    print("highlight annotations:", annotation_counts.get("Highlight", 0))
    print("max highlights on one page:", diagnostics.max_highlights_on_one_page)
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
    print(
        "output contains revised-only text:",
        _contains_revised_only_text(
            original_extracted.text,
            revised_extracted.text,
            output_text,
        ),
    )
    print("output differs from revised bytes:", output_bytes != revised_bytes)

    unwanted_count = sum(
        annotation_counts.get(annotation_type, 0)
        for annotation_type in UNWANTED_ANNOTATION_TYPES
    )

    if unwanted_count:
        print("WARNING: output contains Square/Text/FreeText/Rect annotations")

    output_document.close()
    return 0


def _unit_count(document: object) -> int:
    pages = getattr(document, "pages")
    return sum(len(page.units) for page in pages)


def _contains_revised_only_text(
    original_text: str,
    revised_text: str,
    output_text: str,
) -> bool:
    original_lines = {
        line.strip()
        for line in original_text.splitlines()
        if line.strip()
    }
    revised_only_lines = [
        line.strip()
        for line in revised_text.splitlines()
        if line.strip() and line.strip() not in original_lines
    ]

    return any(line in output_text for line in revised_only_lines)


if __name__ == "__main__":
    raise SystemExit(main())
