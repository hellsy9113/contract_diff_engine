from __future__ import annotations

import logging
from collections import Counter
from typing import Literal

from contract_diff.alignment.structured_alignment import align_structured_blocks
from contract_diff.comparison.structured_changes import build_changes_from_alignment
from contract_diff.extraction.structured.pdf_profiler import profile_pdf
from contract_diff.extraction.structured.pipeline import (
    extract_and_process_pdf,
    get_document_comparison_blocks,
)
from contract_diff.rendering.diagnostics import analyze_rendered_pdf
from contract_diff.rendering.pdf_renderer_v2 import render_changes_to_pdf
from contract_diff.reporting.comparison_report import (
    ComparisonReport,
    build_comparison_report,
)

logger = logging.getLogger(__name__)

OutputBase = Literal["original", "revised"]


def compare_pdf_bytes_v2(
    original_bytes: bytes,
    revised_bytes: bytes,
    output_base: OutputBase = "revised",
) -> tuple[bytes, ComparisonReport]:
    """
    Run the structured v2 PDF comparison pipeline without touching the v1 engine.
    """

    if output_base not in {"original", "revised"}:
        raise ValueError("output_base must be 'original' or 'revised'.")

    original_profile = profile_pdf(original_bytes)
    revised_profile = profile_pdf(revised_bytes)
    original_document = extract_and_process_pdf(original_bytes)
    revised_document = extract_and_process_pdf(revised_bytes)
    original_blocks = get_document_comparison_blocks(original_document)
    revised_blocks = get_document_comparison_blocks(revised_document)

    logger.debug("v2 original pages: %s", original_profile.page_count)
    logger.debug("v2 revised pages: %s", revised_profile.page_count)
    logger.debug("v2 original blocks: %s", len(original_blocks))
    logger.debug("v2 revised blocks: %s", len(revised_blocks))

    matches = align_structured_blocks(original_blocks, revised_blocks)
    changes = build_changes_from_alignment(matches)
    change_counts = Counter(change.change_type for change in changes)
    logger.debug("v2 changes by type: %s", dict(change_counts))

    base_pdf_bytes = revised_bytes if output_base == "revised" else original_bytes
    output_pdf_bytes = render_changes_to_pdf(base_pdf_bytes, changes)
    render_diagnostics = analyze_rendered_pdf(output_pdf_bytes)
    report = build_comparison_report(
        original_profile=original_profile,
        revised_profile=revised_profile,
        changes=changes,
        render_diagnostics=render_diagnostics,
    )
    logger.debug(
        "v2 report confidence: %s",
        report.comparison_quality.confidence,
    )

    return output_pdf_bytes, report
