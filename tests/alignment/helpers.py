from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.models.document.metadata import DocumentMetadata
from contract_diff.parsing.enums.clause_type import ClauseType
from contract_diff.parsing.enums.numbering_style import NumberingStyle
from contract_diff.parsing.models.clause import Clause
from contract_diff.parsing.models.section import Section
from contract_diff.parsing.models.source_reference import SourceReference
from contract_diff.parsing.models.structured_document import StructuredDocument


def make_source_reference(id_suffix: str, page_number: int = 1) -> SourceReference:
    return SourceReference(
        page_number=page_number,
        source_unit_ids=(f"unit-{id_suffix}",),
        source_page_ids=(f"page-{page_number}",),
        source_block_ids=(f"block-{id_suffix}",),
        source_line_ids=(f"line-{id_suffix}",),
        source_span_ids=(f"span-{id_suffix}",),
    )


def make_section(
    section_id: str,
    title: str,
    clause_ids: tuple[str, ...] = (),
) -> Section:
    return Section(
        id=section_id,
        number=None,
        title=title,
        level=1,
        numbering_style=NumberingStyle.DECIMAL,
        page_number=1,
        source_reference=make_source_reference(section_id),
        clause_ids=clause_ids,
    )


def make_clause(
    clause_id: str,
    text: str,
    number: str | None = None,
    section_id: str | None = "section-1",
    title: str | None = None,
) -> Clause:
    return Clause(
        id=clause_id,
        number=number,
        title=title,
        text=text,
        clause_type=ClauseType.STANDARD,
        section_id=section_id,
        page_number=1,
        source_reference=make_source_reference(clause_id),
    )


def make_document(
    clauses: tuple[Clause, ...],
    sections: tuple[Section, ...] | None = None,
) -> StructuredDocument:
    if sections is None:
        sections = (
            make_section(
                section_id="section-1",
                title="Payment Terms",
                clause_ids=tuple(clause.id for clause in clauses),
            ),
        )

    return StructuredDocument(
        format=DocumentFormat.PDF,
        metadata=DocumentMetadata(
            filename="contract.pdf",
            extension=".pdf",
            size_bytes=100,
            page_count=1,
        ),
        sections=sections,
        clauses=clauses,
        paragraphs=(),
        list_items=(),
    )
