from pydantic import BaseModel, ConfigDict

from contract_diff.parsing.enums.numbering_style import NumberingStyle
from contract_diff.parsing.models.source_reference import SourceReference


class Section(BaseModel):
    """
    Visible document section or article heading.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    number: str | None

    title: str

    level: int

    numbering_style: NumberingStyle

    page_number: int

    source_reference: SourceReference

    clause_ids: tuple[str, ...] = ()
