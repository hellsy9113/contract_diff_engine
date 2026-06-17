# src/contract_diff/extraction/exceptions/extraction.py


class ExtractionError(Exception):
    """
    Base class for every extraction-related error.
    """

    pass


class UnsupportedFormatError(ExtractionError):
    """
    Raised when the document format is not supported.
    """

    pass


class InvalidDocumentError(ExtractionError):
    """
    Raised when the document is malformed or unreadable.
    """

    pass


class CorruptedDocumentError(ExtractionError):
    """
    Raised when the document appears to be corrupted.
    """

    pass


class ExtractionFailedError(ExtractionError):
    """
    Raised when extraction fails unexpectedly.
    """

    pass
