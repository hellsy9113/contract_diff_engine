from pydantic import BaseModel, ConfigDict

from contract_diff.parsing.enums.clause_type import ClauseType
from contract_diff.parsing.models.source_reference import SourceReference


class Clause(BaseModel):
    """
    Deterministically parsed clause.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    number: str | None

    title: str | None = None

    text: str

    clause_type: ClauseType

    section_id: str | None

    page_number: int

    source_reference: SourceReference

    paragraph_ids: tuple[str, ...] = ()

    list_item_ids: tuple[str, ...] = ()
