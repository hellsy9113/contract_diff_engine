# src/contract_diff/extraction/interfaces/reader.py

from abc import ABC, abstractmethod
from typing import BinaryIO

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.models.document.extracted_document import ExtractedDocument


class DocumentReader(ABC):
    """
    Base interface for every document reader.

    A reader is responsible for extracting one specific
    document format.
    """

    @property
    @abstractmethod
    def supported_format(self) -> DocumentFormat:
        """
        Returns the format supported by this reader.
        """
        raise NotImplementedError

    @abstractmethod
    def can_read(self, stream: BinaryIO) -> bool:
        """
        Performs any reader-specific capability checks.

        Example:
        - encrypted PDF
        - malformed DOCX
        """
        raise NotImplementedError

    @abstractmethod
    def extract(
        self,
        stream: BinaryIO,
        filename: str,
    ) -> ExtractedDocument:
        """
        Extracts the document into the canonical model.
        """
        raise NotImplementedError
