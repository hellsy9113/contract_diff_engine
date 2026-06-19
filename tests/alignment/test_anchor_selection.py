from contract_diff.alignment.enums.alignment_status import AlignmentStatus
from contract_diff.alignment.services.clause_alignment_service import (
    ClauseAlignmentService,
)
from tests.alignment.helpers import make_clause, make_document


def test_original_only_clause_receives_previous_matched_revised_anchor() -> None:
    original = make_document(
        (
            make_clause("orig-1", "Payment shall be made in 30 days.", "1.1"),
            make_clause("orig-2", "Supplier shall maintain insurance.", "1.2"),
        )
    )
    revised = make_document(
        (make_clause("rev-1", "Payment shall be made in 30 days.", "1.1"),)
    )

    aligned = ClauseAlignmentService().align(original, revised)

    assert aligned[1].status is AlignmentStatus.ORIGINAL_ONLY
    assert aligned[1].revised_anchor_clause_id == "rev-1"


def test_original_only_clause_receives_next_matched_revised_anchor() -> None:
    original = make_document(
        (
            make_clause("orig-1", "Supplier shall maintain insurance.", "1.1"),
            make_clause("orig-2", "Payment shall be made in 30 days.", "1.2"),
        )
    )
    revised = make_document(
        (make_clause("rev-1", "Payment shall be made in 30 days.", "1.2"),)
    )

    aligned = ClauseAlignmentService().align(original, revised)

    assert aligned[0].status is AlignmentStatus.ORIGINAL_ONLY
    assert aligned[0].revised_anchor_clause_id == "rev-1"


def test_original_only_clause_warns_when_no_revised_anchor_exists() -> None:
    original = make_document(
        (make_clause("orig-1", "Supplier shall maintain insurance.", "1.1"),)
    )
    revised = make_document(())

    aligned = ClauseAlignmentService().align(original, revised)

    assert aligned[0].status is AlignmentStatus.ORIGINAL_ONLY
    assert aligned[0].revised_anchor_clause_id is None
    assert aligned[0].warnings == ("NO_REVISED_ANCHOR_FOUND",)
