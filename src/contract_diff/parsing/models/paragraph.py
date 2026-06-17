from pydantic import BaseModel, ConfigDict

from contract_diff.parsing.models.source_reference import SourceReference


class Paragraph(BaseModel):
    """
    Non-heading prose attached to the current clause when possible.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    text: str

    page_number: int

    clause_id: str | None = None

    source_reference: SourceReference
