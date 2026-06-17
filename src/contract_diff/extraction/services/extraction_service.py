from __future__ import annotations

from typing import BinaryIO

from contract_diff.extraction.exceptions.extraction import (
    InvalidDocumentError,
    UnsupportedFormatError,
)
from contract_diff.extraction.identification.format_detector import FormatDetector
from contract_diff.extraction.registry.reader_registry import ReaderRegistry
from contract_diff.models.document.extracted_document import ExtractedDocument


class ExtractionService:
    """
    High-level orchestration service for document extraction.

    This class coordinates:

        • format detection
        • reader lookup
        • capability validation
        • extraction

    It contains NO extraction logic itself.
    """

    def __init__(
        self,
        registry: ReaderRegistry,
    ) -> None:
        self._registry = registry

    def extract(
        self,
        stream: BinaryIO,
        filename: str,
    ) -> ExtractedDocument:
        """
        Extract a document into the canonical representation.
        """

        document_format = FormatDetector.detect(stream)

        if document_format.name == "UNKNOWN":
            raise UnsupportedFormatError("Unable to determine document format.")

        reader = self._registry.get(document_format)

        if not reader.can_read(stream):
            raise InvalidDocumentError(
                f"The {document_format.value.upper()} document cannot be processed."
            )

        return reader.extract(
            stream=stream,
            filename=filename,
        )
