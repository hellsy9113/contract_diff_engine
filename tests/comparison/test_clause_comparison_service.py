from contract_diff.alignment.enums.alignment_status import AlignmentStatus
from contract_diff.alignment.models.aligned_clause import AlignedClause
from contract_diff.alignment.models.alignment_score import AlignmentScore
from contract_diff.comparison.enums.change_type import ChangeType
from contract_diff.comparison.enums.fragment_operation import FragmentOperation
from contract_diff.comparison.services.clause_comparison_service import (
    ClauseComparisonService,
)
from tests.alignment.helpers import make_clause, make_document


def zero_score() -> AlignmentScore:
    return AlignmentScore(
        overall=0,
        clause_number_score=0,
        heading_score=0,
        section_score=0,
        text_score=0,
        position_score=0,
    )


def test_matched_identical_clauses_become_unchanged() -> None:
    original = make_clause("orig-1", "The Buyer shall pay within 30 days.", "1.1")
    revised = make_clause("rev-1", "The Buyer shall pay within 30 days.", "1.1")
    aligned = AlignedClause(
        id="align-1",
        status=AlignmentStatus.MATCHED,
        original_clause_id="orig-1",
        revised_clause_id="rev-1",
        revised_anchor_clause_id="rev-1",
        score=zero_score(),
        reason="test",
    )

    compared = ClauseComparisonService().compare(
        compared_clause_id="cmp-1",
        aligned_clause=aligned,
        original_clause=original,
        revised_clause=revised,
        revised_anchor_clause=revised,
        original_sections={},
        revised_sections={},
    )

    assert compared.change_type is ChangeType.UNCHANGED
    assert compared.fragments == ()


def test_matched_changed_clauses_become_modified_with_fragments() -> None:
    original = make_clause("orig-1", "The Buyer shall pay within 30 days.", "1.1")
    revised = make_clause("rev-1", "The Buyer shall pay within 45 days.", "1.1")
    aligned = AlignedClause(
        id="align-1",
        status=AlignmentStatus.MATCHED,
        original_clause_id="orig-1",
        revised_clause_id="rev-1",
        revised_anchor_clause_id="rev-1",
        score=zero_score(),
        reason="test",
    )

    compared = ClauseComparisonService().compare(
        compared_clause_id="cmp-1",
        aligned_clause=aligned,
        original_clause=original,
        revised_clause=revised,
        revised_anchor_clause=revised,
        original_sections={},
        revised_sections={},
    )

    assert compared.change_type is ChangeType.MODIFIED
    assert compared.original_text == "The Buyer shall pay within 30 days."
    assert compared.revised_text == "The Buyer shall pay within 45 days."
    assert FragmentOperation.DELETED in {
        fragment.operation for fragment in compared.fragments
    }
    assert FragmentOperation.INSERTED in {
        fragment.operation for fragment in compared.fragments
    }
    assert compared.original_source_span_ids == ("span-orig-1",)
    assert compared.revised_source_span_ids == ("span-rev-1",)


def test_removed_clause_preserves_revised_anchor() -> None:
    original = make_clause("orig-1", "Supplier shall maintain insurance.", "1.2")
    revised_anchor = make_clause("rev-1", "The Buyer shall pay within 30 days.", "1.1")
    aligned = AlignedClause(
        id="align-1",
        status=AlignmentStatus.ORIGINAL_ONLY,
        original_clause_id="orig-1",
        revised_clause_id=None,
        revised_anchor_clause_id="rev-1",
        score=zero_score(),
        reason="test",
    )

    compared = ClauseComparisonService().compare(
        compared_clause_id="cmp-1",
        aligned_clause=aligned,
        original_clause=original,
        revised_clause=None,
        revised_anchor_clause=revised_anchor,
        original_sections={},
        revised_sections={},
    )

    assert compared.change_type is ChangeType.REMOVED
    assert compared.original_text == "Supplier shall maintain insurance."
    assert compared.revised_text is None
    assert compared.revised_anchor_clause_id == "rev-1"
    assert compared.revised_page_number == revised_anchor.page_number
    assert compared.revised_source_span_ids == ("span-rev-1",)


def test_added_clause_uses_revised_clause_as_anchor() -> None:
    revised = make_clause(
        "rev-1",
        "Supplier shall maintain cybersecurity insurance.",
        "1.3",
    )
    aligned = AlignedClause(
        id="align-1",
        status=AlignmentStatus.REVISED_ONLY,
        original_clause_id=None,
        revised_clause_id="rev-1",
        revised_anchor_clause_id="rev-1",
        score=zero_score(),
        reason="test",
    )

    compared = ClauseComparisonService().compare(
        compared_clause_id="cmp-1",
        aligned_clause=aligned,
        original_clause=None,
        revised_clause=revised,
        revised_anchor_clause=revised,
        original_sections={},
        revised_sections={},
    )

    assert compared.change_type is ChangeType.ADDED
    assert compared.original_text is None
    assert compared.revised_text == "Supplier shall maintain cybersecurity insurance."
    assert compared.revised_anchor_clause_id == "rev-1"


def test_heading_comes_from_revised_section_when_available() -> None:
    original = make_clause("orig-1", "The Buyer shall pay within 30 days.", "1.1")
    revised = make_clause("rev-1", "The Buyer shall pay within 45 days.", "1.1")
    original_document = make_document((original,))
    revised_document = make_document((revised,))
    aligned = AlignedClause(
        id="align-1",
        status=AlignmentStatus.MATCHED,
        original_clause_id="orig-1",
        revised_clause_id="rev-1",
        revised_anchor_clause_id="rev-1",
        score=zero_score(),
        reason="test",
    )

    compared = ClauseComparisonService().compare(
        compared_clause_id="cmp-1",
        aligned_clause=aligned,
        original_clause=original,
        revised_clause=revised,
        revised_anchor_clause=revised,
        original_sections={
            section.id: section for section in original_document.sections
        },
        revised_sections={
            section.id: section for section in revised_document.sections
        },
    )

    assert compared.heading == "Payment Terms"
