from pydantic import BaseModel, ConfigDict

from contract_diff.parsing.enums.numbering_style import NumberingStyle
from contract_diff.parsing.models.source_reference import SourceReference


class ListItem(BaseModel):
    """
    Structured contract list item.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    marker: str

    text: str

    numbering_style: NumberingStyle

    page_number: int

    clause_id: str | None = None

    source_reference: SourceReference
