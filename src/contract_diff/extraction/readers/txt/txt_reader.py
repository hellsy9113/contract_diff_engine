# src/contract_diff/extraction/readers/txt/txt_reader.py

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.extraction.exceptions.extraction import (
    InvalidDocumentError,
)
from contract_diff.extraction.interfaces.reader import DocumentReader
from contract_diff.models.document.block import Block
from contract_diff.models.document.extracted_document import ExtractedDocument
from contract_diff.models.document.line import Line
from contract_diff.models.document.metadata import DocumentMetadata
from contract_diff.models.document.page import Page
from contract_diff.models.document.span import Span


class TxtReader(DocumentReader):
    """
    Reader for UTF-8 plain text documents.
    """

    @property
    def supported_format(self) -> DocumentFormat:
        return DocumentFormat.TXT

    def can_read(self, stream: BinaryIO) -> bool:
        """
        Returns True if the stream is valid UTF-8.
        """

        position = stream.tell()

        try:
            stream.seek(0)
            stream.read().decode("utf-8")
            return True

        except UnicodeDecodeError:
            return False

        finally:
            stream.seek(position)

    def extract(
        self,
        stream: BinaryIO,
        filename: str,
    ) -> ExtractedDocument:
        """
        Extract a TXT document.
        """

        position = stream.tell()

        try:
            stream.seek(0)
            raw_bytes = stream.read()

            try:
                text = raw_bytes.decode("utf-8")

            except UnicodeDecodeError as exc:
                raise InvalidDocumentError("Text document is not valid UTF-8.") from exc

            metadata = DocumentMetadata(
                filename=filename,
                extension=Path(filename).suffix.lower(),
                size_bytes=len(raw_bytes),
                page_count=1,
            )

            page = Page(
                id="page-1",
                page_number=1,
                blocks=(
                    Block(
                        id="block-1",
                        lines=(
                            Line(
                                id="line-1",
                                spans=(
                                    Span(
                                        id="span-1",
                                        text=text,
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            )

            return ExtractedDocument(
                format=DocumentFormat.TXT,
                metadata=metadata,
                pages=(page,),
            )

        finally:
            stream.seek(position)
