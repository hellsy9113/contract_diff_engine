from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.models.document.metadata import DocumentMetadata
from contract_diff.normalization.models.normalized_document import NormalizedDocument
from contract_diff.normalization.models.normalized_page import NormalizedPage
from contract_diff.normalization.models.normalized_text_unit import (
    NormalizedTextUnit,
)
from contract_diff.parsing.enums.clause_type import ClauseType
from contract_diff.parsing.services.parsing_service import ParsingService


def make_unit(
    unit_id: str,
    text: str,
    source_span_ids: tuple[str, ...],
    page_number: int = 1,
) -> NormalizedTextUnit:
    return NormalizedTextUnit(
        id=unit_id,
        text=text,
        page_number=page_number,
        source_page_id=f"page-{page_number}",
        source_block_id=f"{unit_id}-block",
        source_line_ids=(f"{unit_id}-line",),
        source_span_ids=source_span_ids,
    )


def make_document(units: tuple[NormalizedTextUnit, ...]) -> NormalizedDocument:
    return NormalizedDocument(
        format=DocumentFormat.PDF,
        metadata=DocumentMetadata(
            filename="contract.pdf",
            extension=".pdf",
            size_bytes=100,
            page_count=1,
        ),
        pages=(
            NormalizedPage(
                id="normalized-page-1",
                page_number=1,
                source_page_id="page-1",
                units=units,
            ),
        ),
    )


def test_parse_groups_clauses_under_sections_and_preserves_sources() -> None:
    document = make_document(
        (
            make_unit("unit-1", "Page 1 of 10", ("span-artifact",)),
            make_unit("unit-2", "1. Definitions", ("span-section-1",)),
            make_unit(
                "unit-3",
                '"Agreement" means this contract.',
                ("span-definition",),
            ),
            make_unit("unit-4", "ARTICLE 2 - PAYMENT", ("span-section-2",)),
            make_unit(
                "unit-5",
                "2.1 The Buyer shall pay within 30 days.",
                ("span-clause-1", "span-clause-2"),
            ),
            make_unit(
                "unit-6",
                "(a) Payment shall be made by wire transfer.",
                ("span-list-item",),
            ),
            make_unit("unit-7", "Late fees may apply.", ("span-paragraph",)),
        )
    )

    structured = ParsingService().parse(document)

    assert len(structured.sections) == 2
    assert structured.sections[0].title == "Definitions"
    assert structured.sections[0].clause_ids == ("clause-1",)
    assert structured.sections[1].title == "PAYMENT"
    assert structured.sections[1].clause_ids == ("clause-2",)

    assert len(structured.clauses) == 2
    assert structured.clauses[0].clause_type is ClauseType.DEFINITION
    assert structured.clauses[0].title == "Agreement"
    assert structured.clauses[0].section_id == "section-1"
    assert structured.clauses[0].source_reference.source_unit_ids == ("unit-3",)
    assert structured.clauses[0].source_reference.source_span_ids == (
        "span-definition",
    )

    assert structured.clauses[1].number == "2.1"
    assert structured.clauses[1].text == "The Buyer shall pay within 30 days."
    assert structured.clauses[1].section_id == "section-2"
    assert structured.clauses[1].list_item_ids == ("list-item-1",)
    assert structured.clauses[1].paragraph_ids == ("paragraph-1",)
    assert structured.clauses[1].source_reference.source_span_ids == (
        "span-clause-1",
        "span-clause-2",
    )

    assert len(structured.list_items) == 1
    assert structured.list_items[0].clause_id == "clause-2"
    assert structured.list_items[0].source_reference.source_unit_ids == ("unit-6",)

    assert len(structured.paragraphs) == 1
    assert structured.paragraphs[0].clause_id == "clause-2"
    assert structured.paragraphs[0].source_reference.source_span_ids == (
        "span-paragraph",
    )

    assert structured.parsing_warnings == ()


def test_parse_returns_warnings_for_ambiguous_structure() -> None:
    document = make_document(
        (
            make_unit(
                "unit-1",
                "1.1 Clause appears before any section.",
                ("span-clause",),
            ),
            make_unit("unit-2", "Loose paragraph.", ("span-paragraph",)),
        )
    )

    structured = ParsingService().parse(document)

    assert structured.sections == ()
    assert len(structured.clauses) == 1
    assert structured.clauses[0].section_id is None
    assert structured.paragraphs[0].clause_id == "clause-1"
    assert structured.parsing_warnings == (
        "Clause clause-1 is not attached to a section.",
    )


def test_parse_warns_for_unattached_paragraph() -> None:
    document = make_document(
        (
            make_unit(
                "unit-1",
                "Loose paragraph without a clause.",
                ("span-paragraph",),
            ),
        )
    )

    structured = ParsingService().parse(document)

    assert structured.clauses == ()
    assert structured.paragraphs[0].clause_id is None
    assert structured.parsing_warnings == (
        "Paragraph paragraph-1 is not attached to a clause.",
    )
