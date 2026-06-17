from io import BytesIO

import pytest

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.extraction.exceptions.extraction import InvalidDocumentError
from contract_diff.extraction.readers.txt.txt_reader import TxtReader


@pytest.fixture
def reader() -> TxtReader:
    return TxtReader()


def test_can_read_valid_utf8(reader: TxtReader) -> None:
    stream = BytesIO(b"Hello World")

    assert reader.can_read(stream)


def test_cannot_read_invalid_utf8(reader: TxtReader) -> None:
    stream = BytesIO(b"\xff\xfe\xfa")

    assert not reader.can_read(stream)


def test_extract_txt(reader: TxtReader) -> None:
    text = "Hello\nContract Diff"

    stream = BytesIO(text.encode("utf-8"))

    document = reader.extract(
        stream=stream,
        filename="sample.txt",
    )

    assert document.format is DocumentFormat.TXT

    assert document.metadata.filename == "sample.txt"

    assert document.metadata.extension == ".txt"

    assert document.metadata.page_count == 1

    assert len(document.pages) == 1

    page = document.pages[0]

    assert page.id == "page-1"
    assert page.page_number == 1
    assert page.bbox is None

    assert len(page.blocks) == 1

    block = page.blocks[0]

    assert block.id == "block-1"
    assert block.bbox is None
    assert len(block.lines) == 1

    line = block.lines[0]

    assert line.id == "line-1"
    assert line.bbox is None
    assert len(line.spans) == 1

    span = line.spans[0]

    assert span.id == "span-1"
    assert span.bbox is None
    assert span.font is None
    assert span.font_size is None
    assert span.flags is None
    assert span.text == text

    assert page.text == text

    assert document.text == text


def test_extract_invalid_utf8(reader: TxtReader) -> None:
    stream = BytesIO(b"\xff\xfe\xfa")

    with pytest.raises(InvalidDocumentError):
        reader.extract(
            stream=stream,
            filename="bad.txt",
        )


def test_extract_restores_stream_position(reader: TxtReader) -> None:
    stream = BytesIO(b"Hello")

    stream.read(2)

    position = stream.tell()

    reader.extract(
        stream=stream,
        filename="sample.txt",
    )

    assert stream.tell() == position
