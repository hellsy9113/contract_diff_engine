from pydantic import BaseModel, ConfigDict

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.models.document.metadata import DocumentMetadata
from contract_diff.models.document.page import Page


class ExtractedDocument(BaseModel):
    """
    Canonical representation produced by document readers.

    Every supported document format must be transformed into
    this representation before entering normalization and parsing.
    """

    model_config = ConfigDict(frozen=True)

    format: DocumentFormat

    metadata: DocumentMetadata

    pages: tuple[Page, ...]

    @property
    def text(self) -> str:
        """
        Returns the full document text by joining pages.
        """

        return "\n".join(page.text for page in self.pages)
