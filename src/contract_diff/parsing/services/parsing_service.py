from __future__ import annotations

from dataclasses import dataclass, field

from contract_diff.normalization.models.normalized_document import (
    NormalizedDocument,
)
from contract_diff.normalization.models.normalized_text_unit import (
    NormalizedTextUnit,
)
from contract_diff.parsing.detectors.clause_number_detector import (
    ClauseNumberDetector,
)
from contract_diff.parsing.detectors.definition_detector import DefinitionDetector
from contract_diff.parsing.detectors.heading_detector import HeadingDetector
from contract_diff.parsing.detectors.list_item_detector import ListItemDetector
from contract_diff.parsing.detectors.page_artifact_detector import (
    PageArtifactDetector,
)
from contract_diff.parsing.enums.clause_type import ClauseType
from contract_diff.parsing.enums.numbering_style import NumberingStyle
from contract_diff.parsing.models.clause import Clause
from contract_diff.parsing.models.list_item import ListItem
from contract_diff.parsing.models.paragraph import Paragraph
from contract_diff.parsing.models.section import Section
from contract_diff.parsing.models.source_reference import SourceReference
from contract_diff.parsing.models.structured_document import StructuredDocument


@dataclass
class _SectionDraft:
    id: str
    number: str | None
    title: str
    level: int
    numbering_style: NumberingStyle
    page_number: int
    source_reference: SourceReference
    clause_ids: list[str] = field(default_factory=list)


@dataclass
class _ClauseDraft:
    id: str
    number: str | None
    title: str | None
    text: str
    clause_type: ClauseType
    section_id: str | None
    page_number: int
    source_reference: SourceReference
    paragraph_ids: list[str] = field(default_factory=list)
    list_item_ids: list[str] = field(default_factory=list)


class ParsingService:
    """
    Deterministic parser from normalized text into legal structure.
    """

    def parse(self, document: NormalizedDocument) -> StructuredDocument:
        section_drafts: list[_SectionDraft] = []
        clause_drafts: list[_ClauseDraft] = []
        paragraphs: list[Paragraph] = []
        list_items: list[ListItem] = []
        warnings: list[str] = []

        current_section_id: str | None = None
        current_clause_id: str | None = None

        for unit in self._iter_units(document):
            if PageArtifactDetector.is_artifact(unit.text):
                continue

            source_reference = SourceReference.from_unit(unit)

            heading = HeadingDetector.detect(unit.text)
            if heading is not None:
                section_id = f"section-{len(section_drafts) + 1}"
                section_drafts.append(
                    _SectionDraft(
                        id=section_id,
                        number=heading.number,
                        title=heading.title,
                        level=heading.level,
                        numbering_style=heading.numbering_style,
                        page_number=unit.page_number,
                        source_reference=source_reference,
                    )
                )
                current_section_id = section_id
                current_clause_id = None
                continue

            definition = DefinitionDetector.detect(unit.text)
            if definition is not None:
                current_clause_id = self._append_clause(
                    clause_drafts=clause_drafts,
                    section_drafts=section_drafts,
                    warnings=warnings,
                    number=None,
                    title=definition.term,
                    text=definition.text,
                    clause_type=ClauseType.DEFINITION,
                    section_id=current_section_id,
                    unit=unit,
                    source_reference=source_reference,
                )
                continue

            list_item = ListItemDetector.detect(unit.text)
            if list_item is not None and current_clause_id is not None:
                list_item_id = f"list-item-{len(list_items) + 1}"
                list_items.append(
                    ListItem(
                        id=list_item_id,
                        marker=list_item.marker,
                        text=list_item.body,
                        numbering_style=list_item.numbering_style,
                        page_number=unit.page_number,
                        clause_id=current_clause_id,
                        source_reference=source_reference,
                    )
                )
                clause = self._clause_by_id(clause_drafts, current_clause_id)
                clause.list_item_ids.append(list_item_id)
                continue

            clause_number = ClauseNumberDetector.detect(unit.text)
            if clause_number is not None:
                current_clause_id = self._append_clause(
                    clause_drafts=clause_drafts,
                    section_drafts=section_drafts,
                    warnings=warnings,
                    number=clause_number.number,
                    title=None,
                    text=clause_number.body,
                    clause_type=(
                        ClauseType.NESTED
                        if clause_number.number.startswith("(")
                        else ClauseType.STANDARD
                    ),
                    section_id=current_section_id,
                    unit=unit,
                    source_reference=source_reference,
                )
                continue

            paragraph_id = f"paragraph-{len(paragraphs) + 1}"
            paragraphs.append(
                Paragraph(
                    id=paragraph_id,
                    text=unit.text,
                    page_number=unit.page_number,
                    clause_id=current_clause_id,
                    source_reference=source_reference,
                )
            )

            if current_clause_id is None:
                warnings.append(
                    f"Paragraph {paragraph_id} is not attached to a clause."
                )
            else:
                clause = self._clause_by_id(clause_drafts, current_clause_id)
                clause.paragraph_ids.append(paragraph_id)

        return StructuredDocument(
            format=document.format,
            metadata=document.metadata,
            sections=self._build_sections(section_drafts),
            clauses=self._build_clauses(clause_drafts),
            paragraphs=tuple(paragraphs),
            list_items=tuple(list_items),
            parsing_warnings=tuple(warnings),
        )

    def _iter_units(
        self,
        document: NormalizedDocument,
    ) -> tuple[NormalizedTextUnit, ...]:
        return tuple(unit for page in document.pages for unit in page.units)

    def _append_clause(
        self,
        clause_drafts: list[_ClauseDraft],
        section_drafts: list[_SectionDraft],
        warnings: list[str],
        number: str | None,
        title: str | None,
        text: str,
        clause_type: ClauseType,
        section_id: str | None,
        unit: NormalizedTextUnit,
        source_reference: SourceReference,
    ) -> str:
        clause_id = f"clause-{len(clause_drafts) + 1}"

        clause_drafts.append(
            _ClauseDraft(
                id=clause_id,
                number=number,
                title=title,
                text=text,
                clause_type=clause_type,
                section_id=section_id,
                page_number=unit.page_number,
                source_reference=source_reference,
            )
        )

        if section_id is None:
            warnings.append(f"Clause {clause_id} is not attached to a section.")
        else:
            self._section_by_id(section_drafts, section_id).clause_ids.append(clause_id)

        return clause_id

    def _section_by_id(
        self,
        section_drafts: list[_SectionDraft],
        section_id: str,
    ) -> _SectionDraft:
        for section in section_drafts:
            if section.id == section_id:
                return section

        raise ValueError(f"Unknown section id: {section_id}")

    def _clause_by_id(
        self,
        clause_drafts: list[_ClauseDraft],
        clause_id: str,
    ) -> _ClauseDraft:
        for clause in clause_drafts:
            if clause.id == clause_id:
                return clause

        raise ValueError(f"Unknown clause id: {clause_id}")

    def _build_sections(
        self,
        section_drafts: list[_SectionDraft],
    ) -> tuple[Section, ...]:
        return tuple(
            Section(
                id=section.id,
                number=section.number,
                title=section.title,
                level=section.level,
                numbering_style=section.numbering_style,
                page_number=section.page_number,
                source_reference=section.source_reference,
                clause_ids=tuple(section.clause_ids),
            )
            for section in section_drafts
        )

    def _build_clauses(
        self,
        clause_drafts: list[_ClauseDraft],
    ) -> tuple[Clause, ...]:
        return tuple(
            Clause(
                id=clause.id,
                number=clause.number,
                title=clause.title,
                text=clause.text,
                clause_type=clause.clause_type,
                section_id=clause.section_id,
                page_number=clause.page_number,
                source_reference=clause.source_reference,
                paragraph_ids=tuple(clause.paragraph_ids),
                list_item_ids=tuple(clause.list_item_ids),
            )
            for clause in clause_drafts
        )
