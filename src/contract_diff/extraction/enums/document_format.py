# Goal: Define the language of our extraction subsystem.
# No extraction logic yet—only the types, interfaces, and
# contracts that every later component will depend on.

# src/contract_diff/extraction/enums/document_format.py

from enum import StrEnum


class DocumentFormat(StrEnum):
    """
    Supported document formats.

    This enum represents the canonical document types understood
    by the extraction subsystem.
    """

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"

    UNKNOWN = "unknown"
