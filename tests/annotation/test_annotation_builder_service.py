from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.enums.highlight_style import HighlightStyle
from contract_diff.annotation.services.annotation_builder_service import (
    AnnotationBuilderService,
)
from contract_diff.comparison.enums.change_type import ChangeType
from contract_diff.comparison.models.compared_clause import ComparedClause
from contract_diff.comparison.models.comparison_result import ComparisonResult
from contract_diff.comparison.models.comparison_summary import ComparisonSummary


def make_compared_clause(
    change_type: ChangeType,
    clause_id_suffix: str,
    revised_clause_id: str | None = None,
    revised_anchor_clause_id: str | None = None,
    revised_page_number: int | None = 4,
    revised_source_span_ids: tuple[str, ...] | None = None,
    warnings: tuple[str, ...] = (),
    missing_revised_clause_id: bool = False,
) -> ComparedClause:
    original_clause_id = None
    original_text = None
    revised_text = None

    if change_type is not ChangeType.ADDED:
        original_clause_id = f"orig-{clause_id_suffix}"
        original_text = "Payment shall be made within 30 days."

    if change_type is not ChangeType.REMOVED:
        if revised_clause_id is None and not missing_revised_clause_id:
            revised_clause_id = f"rev-{clause_id_suffix}"
        revised_anchor_clause_id = revised_anchor_clause_id or revised_clause_id
        revised_text = "Payment shall be made within 45 days."
    else:
        revised_anchor_clause_id = (
            revised_anchor_clause_id or f"rev-anchor-{clause_id_suffix}"
        )

    return ComparedClause(
        id=f"cmp-{clause_id_suffix}",
        change_type=change_type,
        original_clause_id=original_clause_id,
        revised_clause_id=revised_clause_id,
        revised_anchor_clause_id=revised_anchor_clause_id,
        original_text=original_text,
        revised_text=revised_text,
        fragments=(),
        heading="Payment Terms",
        original_page_number=3,
        revised_page_number=revised_page_number,
        original_source_unit_ids=(f"unit-orig-{clause_id_suffix}",),
        revised_source_unit_ids=(f"unit-rev-{clause_id_suffix}",),
        original_source_span_ids=(f"span-orig-{clause_id_suffix}",),
        revised_source_span_ids=revised_source_span_ids
        if revised_source_span_ids is not None
        else (f"span-rev-{clause_id_suffix}",),
        warnings=warnings,
    )


def make_comparison_result(
    compared_clauses: tuple[ComparedClause, ...],
    warnings: tuple[str, ...] = (),
) -> ComparisonResult:
    return ComparisonResult(
        compared_clauses=compared_clauses,
        summary=ComparisonSummary(
            total=len(compared_clauses),
            unchanged=count(compared_clauses, ChangeType.UNCHANGED),
            modified=count(compared_clauses, ChangeType.MODIFIED),
            added=count(compared_clauses, ChangeType.ADDED),
            removed=count(compared_clauses, ChangeType.REMOVED),
        ),
        warnings=warnings,
    )


def count(
    compared_clauses: tuple[ComparedClause, ...],
    change_type: ChangeType,
) -> int:
    return sum(
        1
        for compared_clause in compared_clauses
        if compared_clause.change_type is change_type
    )


def test_unchanged_clauses_create_no_annotation() -> None:
    comparison = make_comparison_result(
        (make_compared_clause(ChangeType.UNCHANGED, "1"),)
    )

    plan = AnnotationBuilderService().build(comparison)

    assert plan.annotations == ()
    assert plan.appendix_entries == ()
    assert plan.summary.total == 0


def test_modified_clauses_create_modified_annotation() -> None:
    comparison = make_comparison_result(
        (make_compared_clause(ChangeType.MODIFIED, "1"),)
    )

    plan = AnnotationBuilderService().build(comparison)

    annotation = plan.annotations[0]
    assert annotation.annotation_type is AnnotationType.MODIFIED
    assert annotation.style is HighlightStyle.MODIFIED_HIGHLIGHT
    assert annotation.target is not None
    assert annotation.target.clause_id == "rev-1"
    assert annotation.popup_text == "Payment shall be made within 30 days."
    assert annotation.page_number == 4


def test_added_clauses_create_added_annotation() -> None:
    comparison = make_comparison_result(
        (make_compared_clause(ChangeType.ADDED, "1"),)
    )

    plan = AnnotationBuilderService().build(comparison)

    annotation = plan.annotations[0]
    assert annotation.annotation_type is AnnotationType.ADDED
    assert annotation.style is HighlightStyle.ADDED_HIGHLIGHT
    assert annotation.target is not None
    assert annotation.target.clause_id == "rev-1"
    assert annotation.popup_text == "Not present in original document"


def test_removed_clauses_create_removed_annotation() -> None:
    comparison = make_comparison_result(
        (
            make_compared_clause(
                ChangeType.REMOVED,
                "1",
                revised_anchor_clause_id="rev-anchor-1",
            ),
        )
    )

    plan = AnnotationBuilderService().build(comparison)

    annotation = plan.annotations[0]
    assert annotation.annotation_type is AnnotationType.REMOVED
    assert annotation.style is HighlightStyle.REMOVED_MARKER
    assert annotation.target is not None
    assert annotation.target.clause_id == "rev-anchor-1"
    assert annotation.target.anchor_type == "revised_anchor_clause"
    assert annotation.popup_text == "Payment shall be made within 30 days."


def test_every_annotation_has_unique_id() -> None:
    comparison = make_comparison_result(
        (
            make_compared_clause(ChangeType.MODIFIED, "1"),
            make_compared_clause(ChangeType.ADDED, "2"),
            make_compared_clause(ChangeType.REMOVED, "3"),
        )
    )

    plan = AnnotationBuilderService().build(comparison)

    ids = tuple(annotation.id for annotation in plan.annotations)
    assert ids == ("ANN-1", "ANN-2", "ANN-3")
    assert len(set(ids)) == len(ids)


def test_appendix_entries_are_created_for_every_annotation() -> None:
    comparison = make_comparison_result(
        (
            make_compared_clause(ChangeType.MODIFIED, "1"),
            make_compared_clause(ChangeType.ADDED, "2"),
        )
    )

    plan = AnnotationBuilderService().build(comparison)

    assert len(plan.appendix_entries) == len(plan.annotations)
    assert plan.appendix_entries[0].annotation_id == plan.annotations[0].id
    assert plan.appendix_entries[0].heading == "Payment Terms"
    assert plan.appendix_entries[0].page_number == 4


def test_warnings_are_created_when_target_cannot_be_resolved() -> None:
    comparison = make_comparison_result(
        (
            make_compared_clause(
                ChangeType.MODIFIED,
                "1",
                revised_clause_id=None,
                revised_page_number=None,
                revised_source_span_ids=(),
                missing_revised_clause_id=True,
            ),
        )
    )

    plan = AnnotationBuilderService().build(comparison)

    annotation = plan.annotations[0]
    assert annotation.target is None
    assert "MISSING_ANNOTATION_TARGET_CLAUSE" in annotation.warnings
    assert "MISSING_ANNOTATION_TARGET_PAGE" in annotation.warnings
    assert "MISSING_ANNOTATION_TARGET_SPANS" in annotation.warnings
    assert "MISSING_ANNOTATION_TARGET_CLAUSE" in plan.warnings
    assert plan.summary.unresolved == 1
