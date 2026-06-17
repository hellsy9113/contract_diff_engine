from __future__ import annotations

from contract_diff.alignment.models.alignment_result import AlignmentResult
from contract_diff.comparison.enums.change_type import ChangeType
from contract_diff.comparison.models.compared_clause import ComparedClause
from contract_diff.comparison.models.comparison_result import ComparisonResult
from contract_diff.comparison.models.comparison_summary import ComparisonSummary
from contract_diff.comparison.services.clause_comparison_service import (
    ClauseComparisonService,
)
from contract_diff.parsing.models.clause import Clause
from contract_diff.parsing.models.section import Section
from contract_diff.parsing.models.structured_document import StructuredDocument


class ComparisonService:
    """
    Converts alignment output into internal change records.
    """

    def __init__(
        self,
        clause_comparison_service: ClauseComparisonService | None = None,
    ) -> None:
        self._clause_comparison_service = (
            clause_comparison_service or ClauseComparisonService()
        )

    def compare(
        self,
        original_document: StructuredDocument,
        revised_document: StructuredDocument,
        alignment_result: AlignmentResult,
    ) -> ComparisonResult:
        original_clauses = self._clause_map(original_document)
        revised_clauses = self._clause_map(revised_document)
        original_sections = self._section_map(original_document)
        revised_sections = self._section_map(revised_document)
        compared_clauses: list[ComparedClause] = []

        for aligned_clause in alignment_result.aligned_clauses:
            original_clause = self._lookup(
                original_clauses,
                aligned_clause.original_clause_id,
            )
            revised_clause = self._lookup(
                revised_clauses,
                aligned_clause.revised_clause_id,
            )
            revised_anchor_clause = self._lookup(
                revised_clauses,
                aligned_clause.revised_anchor_clause_id,
            )
            compared_clauses.append(
                self._clause_comparison_service.compare(
                    compared_clause_id=f"cmp-{len(compared_clauses) + 1}",
                    aligned_clause=aligned_clause,
                    original_clause=original_clause,
                    revised_clause=revised_clause,
                    revised_anchor_clause=revised_anchor_clause,
                    original_sections=original_sections,
                    revised_sections=revised_sections,
                )
            )

        compared = tuple(compared_clauses)

        return ComparisonResult(
            compared_clauses=compared,
            summary=self._summary(compared),
            warnings=self._warnings(compared),
        )

    def _clause_map(self, document: StructuredDocument) -> dict[str, Clause]:
        return {clause.id: clause for clause in document.clauses}

    def _section_map(self, document: StructuredDocument) -> dict[str, Section]:
        return {section.id: section for section in document.sections}

    def _lookup(
        self,
        clauses: dict[str, Clause],
        clause_id: str | None,
    ) -> Clause | None:
        if clause_id is None:
            return None

        return clauses.get(clause_id)

    def _summary(
        self,
        compared_clauses: tuple[ComparedClause, ...],
    ) -> ComparisonSummary:
        return ComparisonSummary(
            total=len(compared_clauses),
            unchanged=self._count(compared_clauses, ChangeType.UNCHANGED),
            modified=self._count(compared_clauses, ChangeType.MODIFIED),
            added=self._count(compared_clauses, ChangeType.ADDED),
            removed=self._count(compared_clauses, ChangeType.REMOVED),
        )

    def _count(
        self,
        compared_clauses: tuple[ComparedClause, ...],
        change_type: ChangeType,
    ) -> int:
        return sum(
            1
            for compared_clause in compared_clauses
            if compared_clause.change_type is change_type
        )

    def _warnings(
        self,
        compared_clauses: tuple[ComparedClause, ...],
    ) -> tuple[str, ...]:
        return tuple(
            warning
            for compared_clause in compared_clauses
            for warning in compared_clause.warnings
        )
