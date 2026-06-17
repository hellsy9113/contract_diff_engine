from pydantic import BaseModel, ConfigDict

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.models.document.metadata import DocumentMetadata
from contract_diff.parsing.models.clause import Clause
from contract_diff.parsing.models.list_item import ListItem
from contract_diff.parsing.models.paragraph import Paragraph
from contract_diff.parsing.models.section import Section


class StructuredDocument(BaseModel):
    """
    Rule-based structural view of a normalized document.
    """

    model_config = ConfigDict(frozen=True)

    format: DocumentFormat

    metadata: DocumentMetadata

    sections: tuple[Section, ...]

    clauses: tuple[Clause, ...]

    paragraphs: tuple[Paragraph, ...]

    list_items: tuple[ListItem, ...]

    parsing_warnings: tuple[str, ...] = ()
