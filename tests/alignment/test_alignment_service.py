import json

from contract_diff.alignment.enums.alignment_status import AlignmentStatus
from contract_diff.alignment.enums.document_similarity_status import (
    DocumentSimilarityStatus,
)
from contract_diff.alignment.services.alignment_service import AlignmentService
from tests.alignment.helpers import make_clause, make_document, make_section


def test_alignment_matches_exact_clause_numbers() -> None:
    original = make_document(
        (
            make_clause("orig-1", "The Buyer shall pay within 30 days.", "3.2"),
        )
    )
    revised = make_document(
        (
            make_clause("rev-1", "The Buyer shall pay within 45 days.", "3.2"),
        )
    )

    result = AlignmentService().align(original, revised)

    assert result.status is DocumentSimilarityStatus.ACCEPTED
    assert result.matched_count == 1
    assert result.aligned_clauses[0].status is AlignmentStatus.MATCHED
    assert result.aligned_clauses[0].original_clause_id == "orig-1"
    assert result.aligned_clauses[0].revised_clause_id == "rev-1"
    assert result.aligned_clauses[0].revised_anchor_clause_id == "rev-1"


def test_alignment_marks_unmatched_original_and_revised_clauses() -> None:
    original = make_document(
        (
            make_clause("orig-1", "The Buyer shall pay within 30 days.", "1.1"),
            make_clause("orig-2", "The Supplier shall maintain insurance.", "1.2"),
        )
    )
    revised = make_document(
        (
            make_clause("rev-1", "The Buyer shall pay within 30 days.", "1.1"),
            make_clause(
                "rev-2",
                "The Buyer may request quarterly audit reports.",
                "1.3",
            ),
        )
    )

    result = AlignmentService(minimum_document_similarity=0).align(original, revised)

    statuses = tuple(aligned.status for aligned in result.aligned_clauses)

    assert statuses == (
        AlignmentStatus.MATCHED,
        AlignmentStatus.ORIGINAL_ONLY,
        AlignmentStatus.REVISED_ONLY,
    )
    assert result.original_only_count == 1
    assert result.revised_only_count == 1
    assert result.aligned_clauses[1].revised_anchor_clause_id == "rev-1"
    assert result.aligned_clauses[2].revised_anchor_clause_id == "rev-2"


def test_alignment_rejects_low_similarity_documents() -> None:
    original = make_document(
        (
            make_clause("orig-1", "The employee may terminate employment.", "1.1"),
        ),
        sections=(make_section("section-1", "Employment"),),
    )
    revised = make_document(
        (
            make_clause("rev-1", "The software license is non-transferable.", "1.1"),
        ),
        sections=(make_section("section-1", "Software License"),),
    )

    result = AlignmentService().align(original, revised)

    assert result.status is DocumentSimilarityStatus.REJECTED
    assert result.aligned_clauses == ()
    assert result.warnings == ("LOW_DOCUMENT_SIMILARITY",)


def test_alignment_result_is_json_serializable() -> None:
    original = make_document(
        (
            make_clause("orig-1", "The Buyer shall pay within 30 days.", "3.2"),
        )
    )
    revised = make_document(
        (
            make_clause("rev-1", "The Buyer shall pay within 45 days.", "3.2"),
        )
    )

    result = AlignmentService().align(original, revised)
    payload = json.loads(result.model_dump_json())

    assert payload["status"] == "accepted"
    assert payload["aligned_clauses"][0]["id"] == "align-1"
    assert payload["aligned_clauses"][0]["status"] == "matched"
