from pydantic import BaseModel, ConfigDict

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.models.document.metadata import DocumentMetadata
from contract_diff.normalization.models.normalized_page import NormalizedPage


class NormalizedDocument(BaseModel):
    """
    Cleaned document text with source references preserved.
    """

    model_config = ConfigDict(frozen=True)

    format: DocumentFormat

    metadata: DocumentMetadata

    pages: tuple[NormalizedPage, ...]

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)
