from io import BytesIO

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.extraction.identification.format_detector import FormatDetector


def test_detect_pdf() -> None:
    stream = BytesIO(b"%PDF-1.7\nrest of file")

    result = FormatDetector.detect(stream)

    assert result is DocumentFormat.PDF


def test_detect_docx() -> None:
    stream = BytesIO(b"PK\x03\x04rest of zip")

    result = FormatDetector.detect(stream)

    assert result is DocumentFormat.DOCX


def test_detect_txt() -> None:
    stream = BytesIO(b"Hello Contract Diff")

    result = FormatDetector.detect(stream)

    assert result is DocumentFormat.TXT


def test_detect_unknown() -> None:
    stream = BytesIO(b"\xff\xfe\xfa\xfb")

    result = FormatDetector.detect(stream)

    assert result is DocumentFormat.UNKNOWN


def test_detector_restores_stream_position() -> None:
    stream = BytesIO(b"%PDF-1.7 content")
    stream.read(5)

    position = stream.tell()

    FormatDetector.detect(stream)

    assert stream.tell() == position
