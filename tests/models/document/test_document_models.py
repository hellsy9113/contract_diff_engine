from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.models.document.block import Block
from contract_diff.models.document.bounding_box import BoundingBox
from contract_diff.models.document.extracted_document import ExtractedDocument
from contract_diff.models.document.line import Line
from contract_diff.models.document.metadata import DocumentMetadata
from contract_diff.models.document.page import Page
from contract_diff.models.document.span import Span


def test_bounding_box_accepts_ordered_coordinates() -> None:
    bbox = BoundingBox(x0=10, y0=20, x1=35, y1=45)

    assert bbox.x0 == 10
    assert bbox.y0 == 20
    assert bbox.x1 == 35
    assert bbox.y1 == 45


def test_bounding_box_rejects_reversed_coordinates() -> None:
    with pytest.raises(ValidationError):
        BoundingBox(x0=10, y0=20, x1=5, y1=45)

    with pytest.raises(ValidationError):
        BoundingBox(x0=10, y0=20, x1=35, y1=15)


def test_document_text_is_computed_from_layout_tree() -> None:
    bbox = BoundingBox(x0=0, y0=0, x1=100, y1=20)

    first_span = Span(
        id="span-1",
        text="Hi",
        bbox=bbox,
        font="Helvetica",
        font_size=12,
        flags=0,
    )
    second_span = Span(
        id="span-2",
        text="!",
        bbox=bbox,
        font="Helvetica-Bold",
        font_size=12,
        flags=1,
    )
    line = Line(
        id="line-1",
        bbox=bbox,
        spans=(first_span, second_span),
    )
    block = Block(
        id="block-1",
        bbox=bbox,
        lines=(line,),
    )
    page = Page(
        id="page-1",
        page_number=1,
        bbox=BoundingBox(x0=0, y0=0, x1=612, y1=792),
        blocks=(block,),
    )
    document = ExtractedDocument(
        format=DocumentFormat.PDF,
        metadata=DocumentMetadata(
            filename="contract.pdf",
            extension=".pdf",
            size_bytes=1024,
            page_count=1,
        ),
        pages=(page,),
    )

    assert first_span.text == "Hi"
    assert second_span.text == "!"
    assert line.text == "Hi!"
    assert block.text == "Hi!"
    assert page.text == "Hi!"
    assert document.text == "Hi!"


def test_document_metadata_reserves_source_metadata_fields() -> None:
    creation_date = datetime(2026, 1, 2, 3, 4, tzinfo=UTC)
    modification_date = datetime(2026, 2, 3, 4, 5, tzinfo=UTC)

    metadata = DocumentMetadata(
        filename="contract.pdf",
        extension=".pdf",
        size_bytes=1024,
        title="Master Services Agreement",
        author="Legal Team",
        creator="Contract Editor",
        producer="PDF Engine",
        creation_date=creation_date,
        modification_date=modification_date,
        page_count=12,
    )

    assert metadata.title == "Master Services Agreement"
    assert metadata.author == "Legal Team"
    assert metadata.creator == "Contract Editor"
    assert metadata.producer == "PDF Engine"
    assert metadata.creation_date == creation_date
    assert metadata.modification_date == modification_date


def test_document_tree_uses_immutable_tuple_collections() -> None:
    span = Span(id="span-1", text="A")
    line = Line(id="line-1", spans=(span,))
    block = Block(id="block-1", lines=(line,))
    page = Page(id="page-1", page_number=1, blocks=(block,))
    document = ExtractedDocument(
        format=DocumentFormat.TXT,
        metadata=DocumentMetadata(
            filename="sample.txt",
            extension=".txt",
            size_bytes=1,
            page_count=1,
        ),
        pages=(page,),
    )

    assert isinstance(line.spans, tuple)
    assert isinstance(block.lines, tuple)
    assert isinstance(page.blocks, tuple)
    assert isinstance(document.pages, tuple)

    with pytest.raises(ValidationError):
        setattr(page, "id", "page-2")
