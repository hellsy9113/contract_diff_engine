from __future__ import annotations

from dataclasses import dataclass

from contract_diff.alignment.enums.alignment_status import AlignmentStatus
from contract_diff.alignment.models.aligned_clause import AlignedClause
from contract_diff.alignment.models.alignment_score import AlignmentScore
from contract_diff.alignment.scoring.clause_similarity import ClauseSimilarityScorer
from contract_diff.parsing.models.structured_document import StructuredDocument


@dataclass(frozen=True)
class _CandidatePair:
    original_index: int
    revised_index: int
    score: AlignmentScore


class ClauseAlignmentService:
    """
    Greedy deterministic clause alignment.
    """

    def __init__(self, minimum_match_score: float = 60.0) -> None:
        self._minimum_match_score = minimum_match_score

    def align(
        self,
        original_document: StructuredDocument,
        revised_document: StructuredDocument,
    ) -> tuple[AlignedClause, ...]:
        matched_pairs = self._match_pairs(original_document, revised_document)
        used_revised_indexes = {
            candidate.revised_index for candidate in matched_pairs.values()
        }
        aligned_clauses: list[AlignedClause] = []

        for original_index, original_clause in enumerate(original_document.clauses):
            match = matched_pairs.get(original_index)

            if match is not None:
                revised_clause = revised_document.clauses[match.revised_index]
                aligned_clauses.append(
                    AlignedClause(
                        id=f"align-{len(aligned_clauses) + 1}",
                        status=AlignmentStatus.MATCHED,
                        original_clause_id=original_clause.id,
                        revised_clause_id=revised_clause.id,
                        revised_anchor_clause_id=revised_clause.id,
                        score=match.score,
                        reason=self._match_reason(match.score),
                    )
                )
                continue

            anchor_id = self._find_revised_anchor(
                original_index,
                matched_pairs,
                revised_document,
            )
            warnings: tuple[str, ...] = ()

            if anchor_id is None:
                warnings = ("NO_REVISED_ANCHOR_FOUND",)

            aligned_clauses.append(
                AlignedClause(
                    id=f"align-{len(aligned_clauses) + 1}",
                    status=AlignmentStatus.ORIGINAL_ONLY,
                    original_clause_id=original_clause.id,
                    revised_clause_id=None,
                    revised_anchor_clause_id=anchor_id,
                    score=self._zero_score(),
                    reason="No revised clause exceeded the match threshold.",
                    warnings=warnings,
                )
            )

        for revised_index, revised_clause in enumerate(revised_document.clauses):
            if revised_index in used_revised_indexes:
                continue

            aligned_clauses.append(
                AlignedClause(
                    id=f"align-{len(aligned_clauses) + 1}",
                    status=AlignmentStatus.REVISED_ONLY,
                    original_clause_id=None,
                    revised_clause_id=revised_clause.id,
                    revised_anchor_clause_id=revised_clause.id,
                    score=self._zero_score(),
                    reason="No original clause matched this revised clause.",
                )
            )

        return tuple(aligned_clauses)

    def _match_pairs(
        self,
        original_document: StructuredDocument,
        revised_document: StructuredDocument,
    ) -> dict[int, _CandidatePair]:
        candidates: list[_CandidatePair] = []

        for original_index, original_clause in enumerate(original_document.clauses):
            for revised_index, revised_clause in enumerate(revised_document.clauses):
                score = ClauseSimilarityScorer.score(
                    original_clause=original_clause,
                    revised_clause=revised_clause,
                    original_document=original_document,
                    revised_document=revised_document,
                    original_index=original_index,
                    revised_index=revised_index,
                )
                candidates.append(
                    _CandidatePair(
                        original_index=original_index,
                        revised_index=revised_index,
                        score=score,
                    )
                )

        candidates.sort(
            key=lambda candidate: (
                candidate.score.overall,
                candidate.score.text_score,
                candidate.score.clause_number_score,
            ),
            reverse=True,
        )

        matched_by_original: dict[int, _CandidatePair] = {}
        used_revised_indexes: set[int] = set()

        for candidate in candidates:
            if candidate.score.overall < self._minimum_match_score:
                continue

            if candidate.original_index in matched_by_original:
                continue

            if candidate.revised_index in used_revised_indexes:
                continue

            matched_by_original[candidate.original_index] = candidate
            used_revised_indexes.add(candidate.revised_index)

        return matched_by_original

    def _find_revised_anchor(
        self,
        original_index: int,
        matched_pairs: dict[int, _CandidatePair],
        revised_document: StructuredDocument,
    ) -> str | None:
        previous_matches = [
            match
            for matched_original_index, match in matched_pairs.items()
            if matched_original_index < original_index
        ]

        if previous_matches:
            previous = max(previous_matches, key=lambda match: match.original_index)
            return revised_document.clauses[previous.revised_index].id

        next_matches = [
            match
            for matched_original_index, match in matched_pairs.items()
            if matched_original_index > original_index
        ]

        if next_matches:
            next_match = min(next_matches, key=lambda match: match.original_index)
            return revised_document.clauses[next_match.revised_index].id

        return None

    def _zero_score(self) -> AlignmentScore:
        return AlignmentScore(
            overall=0.0,
            clause_number_score=0.0,
            heading_score=0.0,
            section_score=0.0,
            text_score=0.0,
            position_score=0.0,
        )

    def _match_reason(self, score: AlignmentScore) -> str:
        if score.clause_number_score == 100.0 and score.text_score >= 80.0:
            return "Exact clause number and high text similarity."

        if score.text_score >= 80.0:
            return "High text similarity exceeded the match threshold."

        return "Best deterministic candidate exceeded the match threshold."
