from contract_diff.annotation.services.annotation_target_resolver import (
    AnnotationTargetResolver,
)
from contract_diff.comparison.enums.change_type import ChangeType
from contract_diff.comparison.models.compared_clause import ComparedClause


def make_compared_clause(
    change_type: ChangeType,
    revised_clause_id: str | None = "rev-1",
    revised_anchor_clause_id: str | None = "rev-anchor-1",
    revised_page_number: int | None = 4,
    revised_source_span_ids: tuple[str, ...] = ("span-rev-1",),
) -> ComparedClause:
    return ComparedClause(
        id=f"cmp-{change_type.value}",
        change_type=change_type,
        original_clause_id="orig-1",
        revised_clause_id=revised_clause_id,
        revised_anchor_clause_id=revised_anchor_clause_id,
        original_text="Payment shall be made within 30 days.",
        revised_text="Payment shall be made within 45 days.",
        fragments=(),
        heading="Payment Terms",
        original_page_number=3,
        revised_page_number=revised_page_number,
        original_source_unit_ids=("unit-orig-1",),
        revised_source_unit_ids=("unit-rev-1",),
        original_source_span_ids=("span-orig-1",),
        revised_source_span_ids=revised_source_span_ids,
    )


def test_modified_annotation_targets_revised_clause_id() -> None:
    compared = make_compared_clause(ChangeType.MODIFIED)

    target, warnings = AnnotationTargetResolver().resolve(compared)

    assert target is not None
    assert target.clause_id == "rev-1"
    assert target.page_number == 4
    assert target.source_span_ids == ("span-rev-1",)
    assert target.anchor_type == "revised_clause"
    assert warnings == ()


def test_added_annotation_targets_revised_clause_id() -> None:
    compared = make_compared_clause(
        change_type=ChangeType.ADDED,
        revised_clause_id="rev-added-1",
        revised_anchor_clause_id="rev-added-1",
    )

    target, warnings = AnnotationTargetResolver().resolve(compared)

    assert target is not None
    assert target.clause_id == "rev-added-1"
    assert target.anchor_type == "revised_clause"
    assert warnings == ()


def test_removed_annotation_targets_revised_anchor_clause_id() -> None:
    compared = make_compared_clause(
        change_type=ChangeType.REMOVED,
        revised_clause_id=None,
        revised_anchor_clause_id="rev-anchor-2",
    )

    target, warnings = AnnotationTargetResolver().resolve(compared)

    assert target is not None
    assert target.clause_id == "rev-anchor-2"
    assert target.anchor_type == "revised_anchor_clause"
    assert warnings == ()


def test_resolver_warns_when_target_cannot_be_resolved() -> None:
    compared = make_compared_clause(
        change_type=ChangeType.MODIFIED,
        revised_clause_id=None,
        revised_page_number=None,
        revised_source_span_ids=(),
    )

    target, warnings = AnnotationTargetResolver().resolve(compared)

    assert target is None
    assert "MISSING_ANNOTATION_TARGET_CLAUSE" in warnings
    assert "MISSING_ANNOTATION_TARGET_PAGE" in warnings
    assert "MISSING_ANNOTATION_TARGET_SPANS" in warnings
