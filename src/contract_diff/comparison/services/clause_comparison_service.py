from __future__ import annotations

from contract_diff.alignment.enums.alignment_status import AlignmentStatus
from contract_diff.alignment.models.aligned_clause import AlignedClause
from contract_diff.comparison.enums.change_type import ChangeType
from contract_diff.comparison.models.compared_clause import ComparedClause
from contract_diff.comparison.models.text_fragment import TextFragment
from contract_diff.comparison.services.text_diff_service import TextDiffService
from contract_diff.parsing.models.clause import Clause
from contract_diff.parsing.models.section import Section


class ClauseComparisonService:
    """
    Converts one aligned clause decision into a comparison change record.
    """

    def __init__(self, text_diff_service: TextDiffService | None = None) -> None:
        self._text_diff_service = text_diff_service or TextDiffService()

    def compare(
        self,
        compared_clause_id: str,
        aligned_clause: AlignedClause,
        original_clause: Clause | None,
        revised_clause: Clause | None,
        revised_anchor_clause: Clause | None,
        original_sections: dict[str, Section],
        revised_sections: dict[str, Section],
    ) -> ComparedClause:
        if aligned_clause.status is AlignmentStatus.MATCHED:
            return self._compare_matched(
                compared_clause_id,
                aligned_clause,
                original_clause,
                revised_clause,
                revised_anchor_clause,
                original_sections,
                revised_sections,
            )

        if aligned_clause.status is AlignmentStatus.ORIGINAL_ONLY:
            return self._compare_removed(
                compared_clause_id,
                aligned_clause,
                original_clause,
                revised_anchor_clause,
                original_sections,
            )

        return self._compare_added(
            compared_clause_id,
            aligned_clause,
            revised_clause,
            revised_sections,
        )

    def _compare_matched(
        self,
        compared_clause_id: str,
        aligned_clause: AlignedClause,
        original_clause: Clause | None,
        revised_clause: Clause | None,
        revised_anchor_clause: Clause | None,
        original_sections: dict[str, Section],
        revised_sections: dict[str, Section],
    ) -> ComparedClause:
        warnings = self._missing_clause_warnings(original_clause, revised_clause)

        if original_clause is None or revised_clause is None:
            return ComparedClause(
                id=compared_clause_id,
                change_type=ChangeType.MODIFIED,
                original_clause_id=aligned_clause.original_clause_id,
                revised_clause_id=aligned_clause.revised_clause_id,
                revised_anchor_clause_id=aligned_clause.revised_anchor_clause_id,
                original_text=self._text(original_clause),
                revised_text=self._text(revised_clause),
                fragments=(),
                heading=self._heading(
                    original_clause,
                    revised_clause,
                    original_sections,
                    revised_sections,
                ),
                original_page_number=self._page_number(original_clause),
                revised_page_number=self._page_number(revised_clause),
                warnings=warnings,
            )

        original_text = original_clause.text
        revised_text = revised_clause.text

        if self._text_diff_service.equivalent(original_text, revised_text):
            change_type = ChangeType.UNCHANGED
            fragments: tuple[TextFragment, ...] = ()
        else:
            change_type = ChangeType.MODIFIED
            fragments = self._text_diff_service.diff(original_text, revised_text)

            if not fragments:
                warnings = (*warnings, "NO_TEXT_DIFF_FOR_MODIFIED_CLAUSE")

        return ComparedClause(
            id=compared_clause_id,
            change_type=change_type,
            original_clause_id=original_clause.id,
            revised_clause_id=revised_clause.id,
            revised_anchor_clause_id=self._anchor_id(
                aligned_clause,
                revised_anchor_clause,
                revised_clause,
            ),
            original_text=original_text,
            revised_text=revised_text,
            fragments=fragments,
            heading=self._heading(
                original_clause,
                revised_clause,
                original_sections,
                revised_sections,
            ),
            original_page_number=original_clause.page_number,
            revised_page_number=revised_clause.page_number,
            original_source_unit_ids=original_clause.source_reference.source_unit_ids,
            revised_source_unit_ids=revised_clause.source_reference.source_unit_ids,
            original_source_span_ids=original_clause.source_reference.source_span_ids,
            revised_source_span_ids=revised_clause.source_reference.source_span_ids,
            warnings=warnings,
        )

    def _compare_removed(
        self,
        compared_clause_id: str,
        aligned_clause: AlignedClause,
        original_clause: Clause | None,
        revised_anchor_clause: Clause | None,
        original_sections: dict[str, Section],
    ) -> ComparedClause:
        warnings: tuple[str, ...] = ()

        if original_clause is None:
            warnings = (*warnings, "MISSING_ORIGINAL_CLAUSE")

        if (
            aligned_clause.revised_anchor_clause_id is None
            or revised_anchor_clause is None
        ):
            warnings = (*warnings, "MISSING_REVISED_ANCHOR")

        return ComparedClause(
            id=compared_clause_id,
            change_type=ChangeType.REMOVED,
            original_clause_id=aligned_clause.original_clause_id,
            revised_clause_id=None,
            revised_anchor_clause_id=aligned_clause.revised_anchor_clause_id,
            original_text=self._text(original_clause),
            revised_text=None,
            fragments=(),
            heading=self._heading(original_clause, None, original_sections, {}),
            original_page_number=self._page_number(original_clause),
            revised_page_number=self._page_number(revised_anchor_clause),
            original_source_unit_ids=self._source_unit_ids(original_clause),
            revised_source_unit_ids=self._source_unit_ids(revised_anchor_clause),
            original_source_span_ids=self._source_span_ids(original_clause),
            revised_source_span_ids=self._source_span_ids(revised_anchor_clause),
            warnings=warnings,
        )

    def _compare_added(
        self,
        compared_clause_id: str,
        aligned_clause: AlignedClause,
        revised_clause: Clause | None,
        revised_sections: dict[str, Section],
    ) -> ComparedClause:
        warnings: tuple[str, ...] = ()

        if revised_clause is None:
            warnings = (*warnings, "MISSING_REVISED_CLAUSE")

        return ComparedClause(
            id=compared_clause_id,
            change_type=ChangeType.ADDED,
            original_clause_id=None,
            revised_clause_id=aligned_clause.revised_clause_id,
            revised_anchor_clause_id=aligned_clause.revised_anchor_clause_id,
            original_text=None,
            revised_text=self._text(revised_clause),
            fragments=(),
            heading=self._heading(None, revised_clause, {}, revised_sections),
            revised_page_number=self._page_number(revised_clause),
            revised_source_unit_ids=self._source_unit_ids(revised_clause),
            revised_source_span_ids=self._source_span_ids(revised_clause),
            warnings=warnings,
        )

    def _missing_clause_warnings(
        self,
        original_clause: Clause | None,
        revised_clause: Clause | None,
    ) -> tuple[str, ...]:
        warnings: tuple[str, ...] = ()

        if original_clause is None:
            warnings = (*warnings, "MISSING_ORIGINAL_CLAUSE")

        if revised_clause is None:
            warnings = (*warnings, "MISSING_REVISED_CLAUSE")

        return warnings

    def _anchor_id(
        self,
        aligned_clause: AlignedClause,
        revised_anchor_clause: Clause | None,
        revised_clause: Clause,
    ) -> str:
        if revised_anchor_clause is not None:
            return revised_anchor_clause.id

        if aligned_clause.revised_anchor_clause_id is not None:
            return aligned_clause.revised_anchor_clause_id

        return revised_clause.id

    def _heading(
        self,
        original_clause: Clause | None,
        revised_clause: Clause | None,
        original_sections: dict[str, Section],
        revised_sections: dict[str, Section],
    ) -> str | None:
        revised_heading = self._section_title(revised_clause, revised_sections)

        if revised_heading is not None:
            return revised_heading

        return self._section_title(original_clause, original_sections)

    def _section_title(
        self,
        clause: Clause | None,
        sections: dict[str, Section],
    ) -> str | None:
        if clause is None or clause.section_id is None:
            return None

        section = sections.get(clause.section_id)

        if section is None:
            return None

        return section.title

    def _text(self, clause: Clause | None) -> str | None:
        if clause is None:
            return None

        return clause.text

    def _page_number(self, clause: Clause | None) -> int | None:
        if clause is None:
            return None

        return clause.page_number

    def _source_unit_ids(self, clause: Clause | None) -> tuple[str, ...]:
        if clause is None:
            return ()

        return clause.source_reference.source_unit_ids

    def _source_span_ids(self, clause: Clause | None) -> tuple[str, ...]:
        if clause is None:
            return ()

        return clause.source_reference.source_span_ids
