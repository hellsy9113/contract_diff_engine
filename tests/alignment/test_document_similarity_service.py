from contract_diff.alignment.enums.document_similarity_status import (
    DocumentSimilarityStatus,
)
from contract_diff.alignment.services.document_similarity_service import (
    DocumentSimilarityService,
)
from tests.alignment.helpers import make_clause, make_document, make_section


def test_scores_exact_documents_as_100() -> None:
    document = make_document(
        (make_clause("clause-1", "The Buyer shall pay within 30 days.", "1.1"),)
    )

    result = DocumentSimilarityService().evaluate(document, document)

    assert result.status is DocumentSimilarityStatus.ACCEPTED
    assert result.overall_score == 100


def test_accepts_similar_documents() -> None:
    original = make_document(
        (make_clause("orig-1", "The Buyer shall pay within 30 days.", "1.1"),)
    )
    revised = make_document(
        (make_clause("rev-1", "The Buyer shall pay within 45 days.", "2.1"),),
        sections=(make_section("section-1", "Payment"),),
    )

    result = DocumentSimilarityService().evaluate(original, revised)

    assert result.status is DocumentSimilarityStatus.ACCEPTED
    assert result.overall_score >= 50


def test_rejects_unrelated_documents_without_exception() -> None:
    original = make_document(
        (make_clause("orig-1", "The employee may terminate employment.", "1.1"),),
        sections=(make_section("section-1", "Employment"),),
    )
    revised = make_document(
        (make_clause("rev-1", "The software license is non-transferable.", "1.1"),),
        sections=(make_section("section-1", "Software License"),),
    )

    result = DocumentSimilarityService().evaluate(original, revised)

    assert result.status is DocumentSimilarityStatus.REJECTED
    assert result.reason == "LOW_DOCUMENT_SIMILARITY"
    assert result.message is not None
    assert result.warnings == ("LOW_DOCUMENT_SIMILARITY",)


def test_clause_count_affects_score() -> None:
    original = make_document(
        (
            make_clause("orig-1", "The Buyer shall pay within 30 days.", "1.1"),
            make_clause("orig-2", "The Supplier shall maintain insurance.", "1.2"),
        )
    )
    revised = make_document(
        (make_clause("rev-1", "The Buyer shall pay within 30 days.", "1.1"),)
    )

    result = DocumentSimilarityService().evaluate(original, revised)

    assert result.clause_count_score == 50
