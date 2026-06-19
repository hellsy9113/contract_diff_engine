from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from contract_diff.comparison.structured_changes import Change
from contract_diff.extraction.structured.models import PdfIntakeReport

SCANNED_WARNING = "PDF appears scanned or image-heavy"
TABLE_WARNING = "Table support is experimental"
COLUMN_WARNING = "Columns detected; comparison quality may vary"
ANNOTATION_WARNING = "PDF has existing annotations"
UNCERTAIN_WARNING = "Many uncertain changes detected"
DENSE_HIGHLIGHT_WARNING = "Dense highlight pages detected"


class DocumentQuality(BaseModel):
    """Intake quality signals for one source document."""

    model_config = ConfigDict(frozen=True)

    page_count: int
    text_char_count: int
    word_count: int
    scanned_likelihood: float = Field(ge=0.0, le=1.0)
    table_likelihood: float = Field(ge=0.0, le=1.0)
    column_likelihood: float = Field(ge=0.0, le=1.0)
    has_existing_annotations: bool
    warnings: list[str]


class ComparisonQuality(BaseModel):
    """Aggregate confidence and diagnostics for one comparison run."""

    model_config = ConfigDict(frozen=True)

    confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[str]
    added_count: int
    deleted_count: int
    modified_count: int
    uncertain_count: int
    dense_highlight_pages: list[int]
    unwanted_annotation_count: int


class ComparisonReport(BaseModel):
    """Complete report that can be returned to a client or persisted later."""

    model_config = ConfigDict(frozen=True)

    original_quality: DocumentQuality
    revised_quality: DocumentQuality
    comparison_quality: ComparisonQuality
    changes: list[Change]


def build_comparison_report(
    original_profile: PdfIntakeReport,
    revised_profile: PdfIntakeReport,
    changes: list[Change],
    render_diagnostics: dict[str, Any],
) -> ComparisonReport:
    """Build a quality report from intake, comparison, and rendering signals."""

    original_quality = _document_quality(original_profile)
    revised_quality = _document_quality(revised_profile)
    added_count = _count_changes(changes, "added")
    deleted_count = _count_changes(changes, "deleted")
    modified_count = _count_changes(changes, "modified")
    uncertain_count = _count_changes(changes, "uncertain")
    dense_highlight_pages = _dense_highlight_pages(render_diagnostics)
    unwanted_annotation_count = _unwanted_annotation_count(render_diagnostics)
    warnings = _comparison_warnings(
        original_profile=original_profile,
        revised_profile=revised_profile,
        changes=changes,
        uncertain_count=uncertain_count,
        dense_highlight_pages=dense_highlight_pages,
    )
    confidence = _confidence(
        original_profile=original_profile,
        revised_profile=revised_profile,
        changes=changes,
        uncertain_count=uncertain_count,
        dense_highlight_pages=dense_highlight_pages,
        unwanted_annotation_count=unwanted_annotation_count,
    )

    return ComparisonReport(
        original_quality=original_quality,
        revised_quality=revised_quality,
        comparison_quality=ComparisonQuality(
            confidence=confidence,
            warnings=warnings,
            added_count=added_count,
            deleted_count=deleted_count,
            modified_count=modified_count,
            uncertain_count=uncertain_count,
            dense_highlight_pages=dense_highlight_pages,
            unwanted_annotation_count=unwanted_annotation_count,
        ),
        changes=changes,
    )


def _document_quality(profile: PdfIntakeReport) -> DocumentQuality:
    return DocumentQuality(
        page_count=profile.page_count,
        text_char_count=profile.text_char_count,
        word_count=profile.word_count,
        scanned_likelihood=profile.scanned_likelihood,
        table_likelihood=profile.table_likelihood,
        column_likelihood=profile.column_likelihood,
        has_existing_annotations=profile.annotation_count > 0,
        warnings=profile.warnings,
    )


def _confidence(
    original_profile: PdfIntakeReport,
    revised_profile: PdfIntakeReport,
    changes: list[Change],
    uncertain_count: int,
    dense_highlight_pages: list[int],
    unwanted_annotation_count: int,
) -> float:
    score = 1.0

    for profile in (original_profile, revised_profile):
        if profile.scanned_likelihood >= 0.70:
            score -= 0.25

        if profile.text_char_count < 200 or profile.word_count < 25:
            score -= 0.12

        if profile.table_likelihood >= 0.55:
            score -= 0.05

        if profile.column_likelihood >= 0.55:
            score -= 0.05

        if profile.annotation_count > 0:
            score -= 0.03

    total_changes = len(changes)

    if total_changes:
        uncertain_ratio = uncertain_count / total_changes
        score -= min(0.30, uncertain_ratio * 0.30)

    if dense_highlight_pages:
        score -= 0.10

    if unwanted_annotation_count:
        score -= min(0.20, unwanted_annotation_count * 0.05)

    return min(1.0, max(0.0, round(score, 4)))


def _comparison_warnings(
    original_profile: PdfIntakeReport,
    revised_profile: PdfIntakeReport,
    changes: list[Change],
    uncertain_count: int,
    dense_highlight_pages: list[int],
) -> list[str]:
    warnings: list[str] = []
    profiles = (original_profile, revised_profile)

    if any(profile.scanned_likelihood >= 0.70 for profile in profiles):
        warnings.append(SCANNED_WARNING)

    if any(profile.table_likelihood >= 0.55 for profile in profiles):
        warnings.append(TABLE_WARNING)

    if any(profile.column_likelihood >= 0.55 for profile in profiles):
        warnings.append(COLUMN_WARNING)

    if any(profile.annotation_count > 0 for profile in profiles):
        warnings.append(ANNOTATION_WARNING)

    if _many_uncertain_changes(len(changes), uncertain_count):
        warnings.append(UNCERTAIN_WARNING)

    if dense_highlight_pages:
        warnings.append(DENSE_HIGHLIGHT_WARNING)

    return warnings


def _many_uncertain_changes(total_changes: int, uncertain_count: int) -> bool:
    if uncertain_count == 0:
        return False

    return uncertain_count >= 3 or uncertain_count / max(1, total_changes) >= 0.25


def _count_changes(changes: list[Change], change_type: str) -> int:
    return sum(1 for change in changes if change.change_type == change_type)


def _dense_highlight_pages(render_diagnostics: dict[str, Any]) -> list[int]:
    dense_pages = render_diagnostics.get("dense_pages", [])

    if not isinstance(dense_pages, list):
        return []

    return [int(page) for page in dense_pages if isinstance(page, int)]


def _unwanted_annotation_count(render_diagnostics: dict[str, Any]) -> int:
    value = render_diagnostics.get("unwanted_annotation_count", 0)

    return value if isinstance(value, int) else 0
