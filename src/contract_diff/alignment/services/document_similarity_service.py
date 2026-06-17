from __future__ import annotations

from contract_diff.alignment.enums.document_similarity_status import (
    DocumentSimilarityStatus,
)
from contract_diff.alignment.models.document_similarity_result import (
    DocumentSimilarityResult,
)
from contract_diff.alignment.scoring.heading_similarity import HeadingSimilarity
from contract_diff.alignment.scoring.text_similarity import TextSimilarity
from contract_diff.parsing.models.clause import Clause
from contract_diff.parsing.models.structured_document import StructuredDocument


class DocumentSimilarityService:
    """
    Similarity gate for deciding whether documents should be compared.
    """

    LOW_DOCUMENT_SIMILARITY_REASON = "LOW_DOCUMENT_SIMILARITY"

    def __init__(self, minimum_required_score: float = 50.0) -> None:
        self._minimum_required_score = minimum_required_score

    def evaluate(
        self,
        original_document: StructuredDocument,
        revised_document: StructuredDocument,
    ) -> DocumentSimilarityResult:
        heading_score = self._heading_similarity(
            original_document,
            revised_document,
        )
        clause_text_score = self._clause_text_similarity(
            original_document.clauses,
            revised_document.clauses,
        )
        clause_count_score = self._count_similarity(
            len(original_document.clauses),
            len(revised_document.clauses),
        )
        document_length_score = self._length_similarity(
            self._clause_text_length(original_document.clauses),
            self._clause_text_length(revised_document.clauses),
        )
        overall_score = round(
            (heading_score * 0.40)
            + (clause_text_score * 0.40)
            + (clause_count_score * 0.10)
            + (document_length_score * 0.10),
            2,
        )

        if overall_score < self._minimum_required_score:
            return DocumentSimilarityResult(
                status=DocumentSimilarityStatus.REJECTED,
                overall_score=overall_score,
                minimum_required_score=self._minimum_required_score,
                heading_score=heading_score,
                clause_text_score=clause_text_score,
                clause_count_score=clause_count_score,
                document_length_score=document_length_score,
                reason=self.LOW_DOCUMENT_SIMILARITY_REASON,
                message=(
                    "The uploaded documents appear to be less than "
                    f"{self._minimum_required_score:g}% similar. Please make sure "
                    "you uploaded two versions of the same contract."
                ),
                warnings=(self.LOW_DOCUMENT_SIMILARITY_REASON,),
            )

        return DocumentSimilarityResult(
            status=DocumentSimilarityStatus.ACCEPTED,
            overall_score=overall_score,
            minimum_required_score=self._minimum_required_score,
            heading_score=heading_score,
            clause_text_score=clause_text_score,
            clause_count_score=clause_count_score,
            document_length_score=document_length_score,
        )

    def _heading_similarity(
        self,
        original_document: StructuredDocument,
        revised_document: StructuredDocument,
    ) -> float:
        original_titles = tuple(section.title for section in original_document.sections)
        revised_titles = tuple(section.title for section in revised_document.sections)

        return HeadingSimilarity.average_best_match(original_titles, revised_titles)

    def _clause_text_similarity(
        self,
        original_clauses: tuple[Clause, ...],
        revised_clauses: tuple[Clause, ...],
    ) -> float:
        if not original_clauses and not revised_clauses:
            return 100.0

        if not original_clauses or not revised_clauses:
            return 0.0

        original_score = self._average_best_clause_score(
            original_clauses,
            revised_clauses,
        )
        revised_score = self._average_best_clause_score(
            revised_clauses,
            original_clauses,
        )

        return round((original_score + revised_score) / 2, 2)

    def _average_best_clause_score(
        self,
        source_clauses: tuple[Clause, ...],
        candidate_clauses: tuple[Clause, ...],
    ) -> float:
        scores = [
            max(
                TextSimilarity.score(source_clause.text, candidate_clause.text)
                for candidate_clause in candidate_clauses
            )
            for source_clause in source_clauses
        ]

        return sum(scores) / len(scores)

    def _count_similarity(self, original_count: int, revised_count: int) -> float:
        if original_count == 0 and revised_count == 0:
            return 100.0

        maximum = max(original_count, revised_count)

        if maximum == 0:
            return 100.0

        return round((min(original_count, revised_count) / maximum) * 100, 2)

    def _length_similarity(self, original_length: int, revised_length: int) -> float:
        if original_length == 0 and revised_length == 0:
            return 100.0

        maximum = max(original_length, revised_length)

        if maximum == 0:
            return 100.0

        return round((min(original_length, revised_length) / maximum) * 100, 2)

    def _clause_text_length(self, clauses: tuple[Clause, ...]) -> int:
        return sum(len(clause.text) for clause in clauses)
