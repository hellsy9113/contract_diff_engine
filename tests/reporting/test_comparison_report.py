from __future__ import annotations

from contract_diff.comparison.structured_changes import Change
from contract_diff.extraction.structured.models import PdfIntakeReport
from contract_diff.reporting.comparison_report import (
    DENSE_HIGHLIGHT_WARNING,
    SCANNED_WARNING,
    UNCERTAIN_WARNING,
    build_comparison_report,
)


def make_profile(
    *,
    text_char_count: int = 5000,
    word_count: int = 700,
    scanned_likelihood: float = 0.0,
    table_likelihood: float = 0.0,
    column_likelihood: float = 0.0,
    annotation_count: int = 0,
    warnings: list[str] | None = None,
) -> PdfIntakeReport:
    return PdfIntakeReport(
        is_valid_pdf=True,
        page_count=3,
        is_encrypted=False,
        has_extractable_text=text_char_count > 0,
        text_char_count=text_char_count,
        word_count=word_count,
        image_count=0,
        annotation_count=annotation_count,
        highlight_annotation_count=0,
        table_likelihood=table_likelihood,
        column_likelihood=column_likelihood,
        scanned_likelihood=scanned_likelihood,
        warnings=warnings or [],
    )


def make_change(change_type: str) -> Change:
    return Change(
        change_id="CHG-0001",
        change_type=change_type,  # type: ignore[arg-type]
        original_text="Original text.",
        revised_text="Revised text.",
        original_location=None,
        revised_location=None,
        changed_fragments=[],
        confidence=1.0,
        section_path=[],
        metadata={},
    )


def test_good_text_pdfs_produce_high_confidence() -> None:
    report = build_comparison_report(
        make_profile(),
        make_profile(),
        [make_change("added"), make_change("modified")],
        {"dense_pages": [], "unwanted_annotation_count": 0},
    )

    assert report.comparison_quality.confidence == 1.0
    assert report.comparison_quality.warnings == []


def test_scanned_like_report_lowers_confidence() -> None:
    report = build_comparison_report(
        make_profile(scanned_likelihood=0.9, text_char_count=20, word_count=3),
        make_profile(),
        [make_change("modified")],
        {"dense_pages": [], "unwanted_annotation_count": 0},
    )

    assert report.comparison_quality.confidence < 0.8
    assert SCANNED_WARNING in report.comparison_quality.warnings


def test_many_uncertain_changes_lower_confidence() -> None:
    changes = [make_change("uncertain") for _ in range(4)]

    report = build_comparison_report(
        make_profile(),
        make_profile(),
        changes,
        {"dense_pages": [], "unwanted_annotation_count": 0},
    )

    assert report.comparison_quality.uncertain_count == 4
    assert report.comparison_quality.confidence < 0.8
    assert UNCERTAIN_WARNING in report.comparison_quality.warnings


def test_dense_highlights_lower_confidence() -> None:
    report = build_comparison_report(
        make_profile(),
        make_profile(),
        [make_change("added")],
        {"dense_pages": [2], "unwanted_annotation_count": 0},
    )

    assert report.comparison_quality.dense_highlight_pages == [2]
    assert report.comparison_quality.confidence == 0.9
    assert DENSE_HIGHLIGHT_WARNING in report.comparison_quality.warnings


def test_counts_are_correct() -> None:
    report = build_comparison_report(
        make_profile(),
        make_profile(),
        [
            make_change("added"),
            make_change("deleted"),
            make_change("modified"),
            make_change("uncertain"),
        ],
        {"dense_pages": [], "unwanted_annotation_count": 2},
    )

    assert report.comparison_quality.added_count == 1
    assert report.comparison_quality.deleted_count == 1
    assert report.comparison_quality.modified_count == 1
    assert report.comparison_quality.uncertain_count == 1
    assert report.comparison_quality.unwanted_annotation_count == 2
