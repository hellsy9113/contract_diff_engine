from __future__ import annotations

import logging
import os
from collections import Counter
from pathlib import Path
from typing import Literal

from contract_diff.comparison.word_diff import build_changes_from_word_diff
from contract_diff.debugging.diff_debug import write_diff_debug_json
from contract_diff.extraction.structured.pdf_profiler import profile_pdf
from contract_diff.extraction.structured.pipeline import extract_and_process_pdf
from contract_diff.extraction.structured.word_stream import build_document_word_stream
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
    *,
    original_filename: str | None = None,
    revised_filename: str | None = None,
    debug: bool = False,
    debug_output_path: str | Path | None = None,
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
    original_word_stream = build_document_word_stream(original_document)
    revised_word_stream = build_document_word_stream(revised_document)

    logger.debug("v2 original pages: %s", original_profile.page_count)
    logger.debug("v2 revised pages: %s", revised_profile.page_count)
    logger.debug("v2 original word tokens: %s", len(original_word_stream.tokens))
    logger.debug("v2 revised word tokens: %s", len(revised_word_stream.tokens))

    changes = build_changes_from_word_diff(original_word_stream, revised_word_stream)
    change_counts = Counter(change.change_type for change in changes)
    logger.debug("v2 changes by type: %s", dict(change_counts))

    base_pdf_bytes = revised_bytes if output_base == "revised" else original_bytes
    output_pdf_bytes = render_changes_to_pdf(base_pdf_bytes, changes)
    render_diagnostics = analyze_rendered_pdf(output_pdf_bytes)

    if _debug_diff_enabled(debug, debug_output_path):
        write_diff_debug_json(
            _debug_output_path(debug_output_path),
            original_file=original_filename,
            revised_file=revised_filename,
            original_stream=original_word_stream,
            revised_stream=revised_word_stream,
            changes=changes,
        )

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


def _debug_diff_enabled(
    debug: bool,
    debug_output_path: str | Path | None,
) -> bool:
    return debug or debug_output_path is not None or _truthy_env("DEBUG_DIFF")


def _debug_output_path(debug_output_path: str | Path | None) -> Path:
    if debug_output_path is not None:
        return Path(debug_output_path)

    configured_path = os.getenv("DEBUG_DIFF_PATH")

    if configured_path:
        return Path(configured_path)

    return Path("diff-debug.json")


def _truthy_env(name: str) -> bool:
    value = os.getenv(name)

    if value is None:
        return False

    return value.strip().casefold() in {"1", "true", "yes", "on"}
