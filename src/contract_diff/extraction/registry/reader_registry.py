# src/contract_diff/extraction/registry/reader_registry.py

"""
Reader registry.

Maps document formats to their corresponding readers.

The registry knows nothing about extraction.
It only stores and retrieves reader implementations.
"""

from __future__ import annotations

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.extraction.exceptions.extraction import (
    UnsupportedFormatError,
)
from contract_diff.extraction.interfaces.reader import DocumentReader


class ReaderRegistry:
    """
    Registry for document readers.
    """

    def __init__(self) -> None:
        self._readers: dict[
            DocumentFormat,
            DocumentReader,
        ] = {}

    def register(
        self,
        reader: DocumentReader,
    ) -> None:
        """
        Register a reader.

        Raises
        ------
        ValueError
            If another reader already supports
            the same document format.
        """

        fmt = reader.supported_format

        if fmt in self._readers:
            raise ValueError(f"Reader already registered for {fmt.value}")

        self._readers[fmt] = reader

    def get(
        self,
        document_format: DocumentFormat,
    ) -> DocumentReader:
        """
        Retrieve a reader.

        Raises
        ------
        UnsupportedFormatError
            If no reader exists.
        """

        try:
            return self._readers[document_format]

        except KeyError as exc:
            raise UnsupportedFormatError(
                f"No reader registered for '{document_format.value}'."
            ) from exc

    def supports(
        self,
        document_format: DocumentFormat,
    ) -> bool:
        """
        Returns whether a reader exists.
        """

        return document_format in self._readers

    @property
    def supported_formats(
        self,
    ) -> tuple[DocumentFormat, ...]:
        """
        Returns all registered formats.
        """

        return tuple(self._readers.keys())
