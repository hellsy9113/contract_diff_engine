from __future__ import annotations

from contract_diff.alignment.enums.alignment_status import AlignmentStatus
from contract_diff.alignment.enums.document_similarity_status import (
    DocumentSimilarityStatus,
)
from contract_diff.alignment.models.aligned_clause import AlignedClause
from contract_diff.alignment.models.alignment_result import AlignmentResult
from contract_diff.alignment.services.clause_alignment_service import (
    ClauseAlignmentService,
)
from contract_diff.alignment.services.document_similarity_service import (
    DocumentSimilarityService,
)
from contract_diff.parsing.models.structured_document import StructuredDocument


class AlignmentService:
    """
    Top-level alignment service with document similarity gate.
    """

    def __init__(
        self,
        minimum_document_similarity: float = 50.0,
        minimum_clause_match_score: float = 60.0,
    ) -> None:
        self._document_similarity_service = DocumentSimilarityService(
            minimum_required_score=minimum_document_similarity,
        )
        self._clause_alignment_service = ClauseAlignmentService(
            minimum_match_score=minimum_clause_match_score,
        )

    def align(
        self,
        original_document: StructuredDocument,
        revised_document: StructuredDocument,
    ) -> AlignmentResult:
        document_similarity = self._document_similarity_service.evaluate(
            original_document,
            revised_document,
        )

        if document_similarity.status is DocumentSimilarityStatus.REJECTED:
            return AlignmentResult(
                status=DocumentSimilarityStatus.REJECTED,
                document_similarity=document_similarity,
                aligned_clauses=(),
                original_only_count=0,
                revised_only_count=0,
                matched_count=0,
                warnings=document_similarity.warnings,
            )

        aligned_clauses = self._clause_alignment_service.align(
            original_document,
            revised_document,
        )
        warnings = self._collect_warnings(aligned_clauses)

        return AlignmentResult(
            status=DocumentSimilarityStatus.ACCEPTED,
            document_similarity=document_similarity,
            aligned_clauses=aligned_clauses,
            original_only_count=self._count_status(
                aligned_clauses,
                AlignmentStatus.ORIGINAL_ONLY,
            ),
            revised_only_count=self._count_status(
                aligned_clauses,
                AlignmentStatus.REVISED_ONLY,
            ),
            matched_count=self._count_status(
                aligned_clauses,
                AlignmentStatus.MATCHED,
            ),
            warnings=warnings,
        )

    def _count_status(
        self,
        aligned_clauses: tuple[AlignedClause, ...],
        status: AlignmentStatus,
    ) -> int:
        return sum(
            1
            for aligned_clause in aligned_clauses
            if aligned_clause.status is status
        )

    def _collect_warnings(
        self,
        aligned_clauses: tuple[AlignedClause, ...],
    ) -> tuple[str, ...]:
        return tuple(
            warning
            for aligned_clause in aligned_clauses
            for warning in aligned_clause.warnings
        )
