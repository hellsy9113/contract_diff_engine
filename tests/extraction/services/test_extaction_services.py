from io import BytesIO
from typing import BinaryIO

import pytest

from contract_diff.extraction.exceptions.extraction import (
    InvalidDocumentError,
    UnsupportedFormatError,
)
from contract_diff.extraction.readers.txt.txt_reader import TxtReader
from contract_diff.extraction.registry.reader_registry import ReaderRegistry
from contract_diff.extraction.services.extraction_service import ExtractionService


@pytest.fixture
def registry() -> ReaderRegistry:
    registry = ReaderRegistry()
    registry.register(TxtReader())
    return registry


@pytest.fixture
def service(registry: ReaderRegistry) -> ExtractionService:
    return ExtractionService(registry)


def test_extract_txt(service: ExtractionService) -> None:
    stream = BytesIO(b"Hello World")

    document = service.extract(
        stream=stream,
        filename="hello.txt",
    )

    assert document.metadata.filename == "hello.txt"

    assert document.text == "Hello World"


def test_unknown_format(service: ExtractionService) -> None:
    stream = BytesIO(b"\xff\xfe\xfa")

    with pytest.raises(UnsupportedFormatError):
        service.extract(
            stream=stream,
            filename="unknown.bin",
        )


def test_missing_reader() -> None:
    registry = ReaderRegistry()

    service = ExtractionService(registry)

    stream = BytesIO(b"%PDF-1.7")

    with pytest.raises(UnsupportedFormatError):
        service.extract(
            stream=stream,
            filename="contract.pdf",
        )


def test_reader_cannot_read(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = ReaderRegistry()

    reader = TxtReader()

    def cannot_read(stream: BinaryIO) -> bool:
        return False

    monkeypatch.setattr(
        reader,
        "can_read",
        cannot_read,
    )

    registry.register(reader)

    service = ExtractionService(registry)

    stream = BytesIO(b"Hello")

    with pytest.raises(InvalidDocumentError):
        service.extract(
            stream=stream,
            filename="hello.txt",
        )
