import pytest

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.extraction.exceptions.extraction import UnsupportedFormatError
from contract_diff.extraction.readers.txt.txt_reader import TxtReader
from contract_diff.extraction.registry.reader_registry import ReaderRegistry


def test_register_reader() -> None:
    registry = ReaderRegistry()
    reader = TxtReader()

    registry.register(reader)

    assert registry.get(DocumentFormat.TXT) is reader


def test_duplicate_registration() -> None:
    registry = ReaderRegistry()

    registry.register(TxtReader())

    with pytest.raises(ValueError):
        registry.register(TxtReader())


def test_supports() -> None:
    registry = ReaderRegistry()

    registry.register(TxtReader())

    assert registry.supports(DocumentFormat.TXT)
    assert not registry.supports(DocumentFormat.PDF)


def test_get_unknown_reader() -> None:
    registry = ReaderRegistry()

    with pytest.raises(UnsupportedFormatError):
        registry.get(DocumentFormat.PDF)


def test_supported_formats() -> None:
    registry = ReaderRegistry()

    registry.register(TxtReader())

    assert registry.supported_formats == (DocumentFormat.TXT,)
