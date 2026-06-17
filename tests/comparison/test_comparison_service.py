import json

from contract_diff.alignment.enums.alignment_status import AlignmentStatus
from contract_diff.alignment.enums.document_similarity_status import (
    DocumentSimilarityStatus,
)
from contract_diff.alignment.models.aligned_clause import AlignedClause
from contract_diff.alignment.models.alignment_result import AlignmentResult
from contract_diff.alignment.models.alignment_score import AlignmentScore
from contract_diff.alignment.models.document_similarity_result import (
    DocumentSimilarityResult,
)
from contract_diff.comparison.enums.change_type import ChangeType
from contract_diff.comparison.services.comparison_service import ComparisonService
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


def similarity_result() -> DocumentSimilarityResult:
    return DocumentSimilarityResult(
        status=DocumentSimilarityStatus.ACCEPTED,
        overall_score=100,
        minimum_required_score=50,
        heading_score=100,
        clause_text_score=100,
        clause_count_score=100,
        document_length_score=100,
    )


def aligned_clause(
    status: AlignmentStatus,
    original_clause_id: str | None,
    revised_clause_id: str | None,
    revised_anchor_clause_id: str | None,
) -> AlignedClause:
    return AlignedClause(
        id="align-test",
        status=status,
        original_clause_id=original_clause_id,
        revised_clause_id=revised_clause_id,
        revised_anchor_clause_id=revised_anchor_clause_id,
        score=zero_score(),
        reason="test",
    )


def alignment_result(aligned_clauses: tuple[AlignedClause, ...]) -> AlignmentResult:
    return AlignmentResult(
        status=DocumentSimilarityStatus.ACCEPTED,
        document_similarity=similarity_result(),
        aligned_clauses=aligned_clauses,
        original_only_count=sum(
            1
            for clause in aligned_clauses
            if clause.status is AlignmentStatus.ORIGINAL_ONLY
        ),
        revised_only_count=sum(
            1
            for clause in aligned_clauses
            if clause.status is AlignmentStatus.REVISED_ONLY
        ),
        matched_count=sum(
            1
            for clause in aligned_clauses
            if clause.status is AlignmentStatus.MATCHED
        ),
    )


def test_comparison_service_builds_summary_counts() -> None:
    original = make_document(
        (
            make_clause(
                "orig-1",
                "This Agreement begins on the Effective Date.",
                "1.1",
            ),
            make_clause("orig-2", "Payment shall be made within 30 days.", "1.2"),
            make_clause("orig-3", "Supplier shall maintain insurance.", "1.3"),
        )
    )
    revised = make_document(
        (
            make_clause(
                "rev-1",
                "This Agreement begins on the Effective Date.",
                "1.1",
            ),
            make_clause("rev-2", "Payment shall be made within 45 days.", "1.2"),
            make_clause(
                "rev-4",
                "Supplier shall maintain cybersecurity insurance.",
                "1.4",
            ),
        )
    )
    alignment = alignment_result(
        (
            aligned_clause(AlignmentStatus.MATCHED, "orig-1", "rev-1", "rev-1"),
            aligned_clause(AlignmentStatus.MATCHED, "orig-2", "rev-2", "rev-2"),
            aligned_clause(AlignmentStatus.ORIGINAL_ONLY, "orig-3", None, "rev-2"),
            aligned_clause(AlignmentStatus.REVISED_ONLY, None, "rev-4", "rev-4"),
        )
    )

    result = ComparisonService().compare(original, revised, alignment)

    assert [clause.change_type for clause in result.compared_clauses] == [
        ChangeType.UNCHANGED,
        ChangeType.MODIFIED,
        ChangeType.REMOVED,
        ChangeType.ADDED,
    ]
    assert result.summary.total == 4
    assert result.summary.unchanged == 1
    assert result.summary.modified == 1
    assert result.summary.removed == 1
    assert result.summary.added == 1
    assert result.warnings == ()


def test_missing_clause_ids_create_warnings() -> None:
    original = make_document(())
    revised = make_document(())
    alignment = alignment_result(
        (
            aligned_clause(
                AlignmentStatus.MATCHED,
                "missing-original",
                "missing-revised",
                None,
            ),
            aligned_clause(
                AlignmentStatus.ORIGINAL_ONLY,
                "missing-original",
                None,
                None,
            ),
            aligned_clause(
                AlignmentStatus.REVISED_ONLY,
                None,
                "missing-revised",
                "missing-revised",
            ),
        )
    )

    result = ComparisonService().compare(original, revised, alignment)

    assert "MISSING_ORIGINAL_CLAUSE" in result.warnings
    assert "MISSING_REVISED_CLAUSE" in result.warnings
    assert "MISSING_REVISED_ANCHOR" in result.warnings


def test_comparison_result_serializes_to_json() -> None:
    original = make_document(
        (
            make_clause("orig-1", "Payment shall be made within 30 days.", "1.1"),
        )
    )
    revised = make_document(
        (
            make_clause("rev-1", "Payment shall be made within 45 days.", "1.1"),
        )
    )
    alignment = alignment_result(
        (
            aligned_clause(AlignmentStatus.MATCHED, "orig-1", "rev-1", "rev-1"),
        )
    )

    result = ComparisonService().compare(original, revised, alignment)
    payload = json.loads(result.model_dump_json())

    assert payload["summary"]["modified"] == 1
    assert payload["compared_clauses"][0]["change_type"] == "modified"
