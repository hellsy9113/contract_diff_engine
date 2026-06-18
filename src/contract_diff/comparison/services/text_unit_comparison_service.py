from __future__ import annotations

import logging
from difflib import SequenceMatcher

from contract_diff.comparison.enums.change_type import ChangeType
from contract_diff.comparison.enums.fragment_operation import FragmentOperation
from contract_diff.comparison.models.compared_clause import ComparedClause
from contract_diff.comparison.models.comparison_result import ComparisonResult
from contract_diff.comparison.models.comparison_summary import ComparisonSummary
from contract_diff.comparison.models.text_fragment import TextFragment
from contract_diff.comparison.services.text_diff_service import TextDiffService
from contract_diff.comparison.utils.text_diff_helpers import (
    MODIFIED_BLOCK_SIMILARITY_THRESHOLD,
    get_changed_fragments,
    normalize_for_alignment,
    similarity_ratio,
)
from contract_diff.normalization.models.normalized_document import NormalizedDocument
from contract_diff.normalization.models.normalized_text_unit import (
    NormalizedTextUnit,
)

logger = logging.getLogger(__name__)


class TextUnitComparisonService:
    """
    Fallback comparison for PDFs that do not parse into clauses.

    It compares normalized line/block text units and preserves revised span IDs
    so the existing annotation and rendering layers can still highlight changes.
    """

    FALLBACK_WARNING = "LINE_LEVEL_FALLBACK_COMPARISON"

    def __init__(self, text_diff_service: TextDiffService | None = None) -> None:
        self._text_diff_service = text_diff_service or TextDiffService()

    def compare(
        self,
        original_document: NormalizedDocument,
        revised_document: NormalizedDocument,
    ) -> ComparisonResult:
        original_units = self._units(original_document)
        revised_units = self._units(revised_document)
        matcher = SequenceMatcher(
            None,
            tuple(self._key(unit) for unit in original_units),
            tuple(self._key(unit) for unit in revised_units),
        )
        compared_clauses: list[ComparedClause] = []
        ops = matcher.get_opcodes()
        insertion_count = 0
        deletion_count = 0
        modification_count = 0
        ignored_count = 0

        logger.debug("original blocks: %s", len(original_units))
        logger.debug("revised blocks: %s", len(revised_units))
        logger.debug("alignment ops: %s", len(ops))

        for tag, original_start, original_end, revised_start, revised_end in ops:
            if tag == "equal":
                ignored_count += original_end - original_start
                continue

            if tag == "replace":
                counts = self._append_replacements(
                    compared_clauses,
                    original_units[original_start:original_end],
                    revised_units[revised_start:revised_end],
                    revised_units,
                    revised_start,
                )
                insertion_count += counts.insertions
                deletion_count += counts.deletions
                modification_count += counts.modifications
                ignored_count += counts.ignored
                continue

            if tag == "delete":
                self._append_removed(
                    compared_clauses,
                    original_units[original_start:original_end],
                    revised_units,
                    revised_start,
                )
                deletion_count += original_end - original_start
                continue

            self._append_added(
                compared_clauses,
                revised_units[revised_start:revised_end],
            )
            insertion_count += revised_end - revised_start

        logger.debug("insertions: %s", insertion_count)
        logger.debug("deletions: %s", deletion_count)
        logger.debug("modifications: %s", modification_count)
        logger.debug(
            "ignored equal/whitespace-only changes: %s",
            ignored_count,
        )

        compared = tuple(compared_clauses)

        return ComparisonResult(
            compared_clauses=compared,
            summary=self._summary(compared),
            warnings=(self.FALLBACK_WARNING,) if compared else (),
        )

    def _append_replacements(
        self,
        compared_clauses: list[ComparedClause],
        original_units: tuple[NormalizedTextUnit, ...],
        revised_units: tuple[NormalizedTextUnit, ...],
        all_revised_units: tuple[NormalizedTextUnit, ...],
        revised_start: int,
    ) -> _ReplacementCounts:
        counts = _ReplacementCounts()
        paired_count = min(len(original_units), len(revised_units))

        for index in range(paired_count):
            original_unit = original_units[index]
            revised_unit = revised_units[index]

            if self._key(original_unit) == self._key(revised_unit):
                counts.ignored += 1
                continue

            similarity = similarity_ratio(original_unit.text, revised_unit.text)

            # A replace opcode can mean either a true edit or unrelated
            # delete+insert. Only classify it as modified when the old and new
            # blocks are similar enough.
            if similarity >= MODIFIED_BLOCK_SIMILARITY_THRESHOLD:
                compared_clauses.append(
                    self._modified(
                        compared_clause_id=self._next_id(compared_clauses),
                        original_unit=original_unit,
                        revised_unit=revised_unit,
                    )
                )
                changed_fragments = get_changed_fragments(
                    original_unit.text,
                    revised_unit.text,
                )
                logger.debug("modified similarity: %.3f", similarity)
                logger.debug("changed fragments: %s", changed_fragments[:5])
                counts.modifications += 1
                continue

            self._append_removed(
                compared_clauses,
                (original_unit,),
                all_revised_units,
                revised_start + index,
            )
            self._append_added(compared_clauses, (revised_unit,))
            counts.deletions += 1
            counts.insertions += 1

        if len(original_units) > paired_count:
            self._append_removed(
                compared_clauses,
                original_units[paired_count:],
                all_revised_units,
                revised_start + paired_count,
            )
            counts.deletions += len(original_units) - paired_count

        if len(revised_units) > paired_count:
            self._append_added(
                compared_clauses,
                revised_units[paired_count:],
            )
            counts.insertions += len(revised_units) - paired_count

        return counts

    def _append_added(
        self,
        compared_clauses: list[ComparedClause],
        revised_units: tuple[NormalizedTextUnit, ...],
    ) -> None:
        for revised_unit in revised_units:
            compared_clauses.append(
                self._added(
                    compared_clause_id=self._next_id(compared_clauses),
                    revised_unit=revised_unit,
                )
            )

    def _append_removed(
        self,
        compared_clauses: list[ComparedClause],
        original_units: tuple[NormalizedTextUnit, ...],
        revised_units: tuple[NormalizedTextUnit, ...],
        revised_index: int,
    ) -> None:
        anchor = self._anchor(revised_units, revised_index)

        for original_unit in original_units:
            compared_clauses.append(
                self._removed(
                    compared_clause_id=self._next_id(compared_clauses),
                    original_unit=original_unit,
                    revised_anchor=anchor,
                )
            )

    def _modified(
        self,
        compared_clause_id: str,
        original_unit: NormalizedTextUnit,
        revised_unit: NormalizedTextUnit,
    ) -> ComparedClause:
        return ComparedClause(
            id=compared_clause_id,
            change_type=ChangeType.MODIFIED,
            original_clause_id=original_unit.id,
            revised_clause_id=revised_unit.id,
            revised_anchor_clause_id=revised_unit.id,
            original_text=original_unit.text,
            revised_text=revised_unit.text,
            fragments=self._changed_fragments(original_unit.text, revised_unit.text),
            original_page_number=original_unit.page_number,
            revised_page_number=revised_unit.page_number,
            original_source_unit_ids=(original_unit.id,),
            revised_source_unit_ids=(revised_unit.id,),
            original_source_span_ids=original_unit.source_span_ids,
            revised_source_span_ids=revised_unit.source_span_ids,
        )

    def _added(
        self,
        compared_clause_id: str,
        revised_unit: NormalizedTextUnit,
    ) -> ComparedClause:
        return ComparedClause(
            id=compared_clause_id,
            change_type=ChangeType.ADDED,
            original_clause_id=None,
            revised_clause_id=revised_unit.id,
            revised_anchor_clause_id=revised_unit.id,
            original_text=None,
            revised_text=revised_unit.text,
            fragments=(),
            revised_page_number=revised_unit.page_number,
            revised_source_unit_ids=(revised_unit.id,),
            revised_source_span_ids=revised_unit.source_span_ids,
        )

    def _removed(
        self,
        compared_clause_id: str,
        original_unit: NormalizedTextUnit,
        revised_anchor: NormalizedTextUnit | None,
    ) -> ComparedClause:
        warnings: tuple[str, ...] = ()

        if revised_anchor is None:
            warnings = ("MISSING_REVISED_ANCHOR",)

        return ComparedClause(
            id=compared_clause_id,
            change_type=ChangeType.REMOVED,
            original_clause_id=original_unit.id,
            revised_clause_id=None,
            revised_anchor_clause_id=(
                revised_anchor.id if revised_anchor is not None else None
            ),
            original_text=original_unit.text,
            revised_text=None,
            fragments=(),
            original_page_number=original_unit.page_number,
            revised_page_number=(
                revised_anchor.page_number if revised_anchor is not None else None
            ),
            original_source_unit_ids=(original_unit.id,),
            revised_source_unit_ids=(
                (revised_anchor.id,) if revised_anchor is not None else ()
            ),
            original_source_span_ids=original_unit.source_span_ids,
            revised_source_span_ids=(
                revised_anchor.source_span_ids if revised_anchor is not None else ()
            ),
            warnings=warnings,
        )

    def _anchor(
        self,
        revised_units: tuple[NormalizedTextUnit, ...],
        revised_index: int,
    ) -> NormalizedTextUnit | None:
        if not revised_units:
            return None

        if revised_index < len(revised_units):
            return revised_units[revised_index]

        return revised_units[-1]

    def _units(
        self,
        document: NormalizedDocument,
    ) -> tuple[NormalizedTextUnit, ...]:
        return tuple(unit for page in document.pages for unit in page.units)

    def _key(self, unit: NormalizedTextUnit) -> str:
        return normalize_for_alignment(unit.text)

    def _next_id(self, compared_clauses: list[ComparedClause]) -> str:
        return f"cmp-text-unit-{len(compared_clauses) + 1}"

    def _changed_fragments(
        self,
        original_text: str,
        revised_text: str,
    ) -> tuple[TextFragment, ...]:
        return tuple(
            TextFragment(
                operation=FragmentOperation.INSERTED,
                sequence_index=index,
                revised_text=fragment,
            )
            for index, fragment in enumerate(
                get_changed_fragments(original_text, revised_text),
                start=1,
            )
        )

    def _summary(
        self,
        compared_clauses: tuple[ComparedClause, ...],
    ) -> ComparisonSummary:
        return ComparisonSummary(
            total=len(compared_clauses),
            unchanged=0,
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


class _ReplacementCounts:
    def __init__(self) -> None:
        self.insertions = 0
        self.deletions = 0
        self.modifications = 0
        self.ignored = 0
