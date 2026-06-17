# src/contract_diff/extraction/identification/format_detector.py

"""
Document format detection.

This module identifies the true document format using file signatures
(magic bytes) and a UTF-8 fallback for plain-text files.

It performs NO extraction.
"""

from __future__ import annotations

from typing import BinaryIO

from contract_diff.extraction.enums.document_format import DocumentFormat


class FormatDetector:
    """
    Detects the true format of an input document.

    Detection priority:

        1. PDF magic bytes
        2. DOCX (ZIP container)
        3. UTF-8 plain text
        4. UNKNOWN
    """

    # Number of bytes needed for signature detection.
    HEADER_SIZE = 8

    # Known file signatures.
    PDF_SIGNATURE = b"%PDF"

    ZIP_SIGNATURE = b"PK\x03\x04"

    @classmethod
    def detect(cls, stream: BinaryIO) -> DocumentFormat:
        """
        Detect the format of a binary stream.

        Parameters
        ----------
        stream:
            Binary file-like object positioned anywhere.

        Returns
        -------
        DocumentFormat
            Detected document format.
        """

        # Preserve caller's stream position.
        current_position = stream.tell()

        try:
            stream.seek(0)
            header = stream.read(cls.HEADER_SIZE)

            # ---------- PDF ----------
            if header.startswith(cls.PDF_SIGNATURE):
                return DocumentFormat.PDF

            # ---------- DOCX ----------
            #
            # DOCX files are ZIP archives.
            #
            # We intentionally classify every ZIP archive as DOCX
            # for now because Version 1 only supports DOCX.
            #
            # Later we will inspect [Content_Types].xml
            # to distinguish DOCX from PPTX/XLSX.
            #
            if header.startswith(cls.ZIP_SIGNATURE):
                return DocumentFormat.DOCX

            # ---------- TXT ----------
            stream.seek(0)

            try:
                stream.read().decode("utf-8")

                return DocumentFormat.TXT

            except UnicodeDecodeError:
                pass

            # ---------- Unknown ----------
            return DocumentFormat.UNKNOWN

        finally:
            # Restore original stream position.
            stream.seek(current_position)
