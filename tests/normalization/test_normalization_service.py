from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.models.document.block import Block
from contract_diff.models.document.extracted_document import ExtractedDocument
from contract_diff.models.document.line import Line
from contract_diff.models.document.metadata import DocumentMetadata
from contract_diff.models.document.page import Page
from contract_diff.models.document.span import Span
from contract_diff.normalization.services.normalization_service import (
    NormalizationService,
)


def test_normalize_document_preserves_source_span_ids() -> None:
    document = ExtractedDocument(
        format=DocumentFormat.PDF,
        metadata=DocumentMetadata(
            filename="contract.pdf",
            extension=".pdf",
            size_bytes=100,
            page_count=1,
        ),
        pages=(
            Page(
                id="page-1",
                page_number=1,
                blocks=(
                    Block(
                        id="block-1",
                        lines=(
                            Line(
                                id="line-1",
                                spans=(Span(id="span-1", text="The Buyer shall pay"),),
                            ),
                            Line(
                                id="line-2",
                                spans=(Span(id="span-2", text="within 30 days."),),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    normalized = NormalizationService().normalize(document)

    page = normalized.pages[0]
    unit = page.units[0]

    assert normalized.format is DocumentFormat.PDF
    assert normalized.metadata is document.metadata
    assert page.id == "normalized-page-1"
    assert page.source_page_id == "page-1"
    assert unit.id == "normalized-unit-1"
    assert unit.text == "The Buyer shall pay within 30 days."
    assert unit.page_number == 1
    assert unit.source_page_id == "page-1"
    assert unit.source_block_id == "block-1"
    assert unit.source_line_ids == ("line-1", "line-2")
    assert unit.source_span_ids == ("span-1", "span-2")
    assert normalized.text == "The Buyer shall pay within 30 days."


def test_normalize_document_skips_empty_units_but_keeps_page() -> None:
    document = ExtractedDocument(
        format=DocumentFormat.TXT,
        metadata=DocumentMetadata(
            filename="empty.txt",
            extension=".txt",
            size_bytes=3,
            page_count=1,
        ),
        pages=(
            Page(
                id="page-1",
                page_number=1,
                blocks=(
                    Block(
                        id="block-1",
                        lines=(
                            Line(
                                id="line-1",
                                spans=(Span(id="span-1", text="   \n\t"),),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    normalized = NormalizationService().normalize(document)

    assert normalized.pages[0].units == ()
    assert normalized.text == ""
