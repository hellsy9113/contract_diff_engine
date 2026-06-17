from pydantic import BaseModel, ConfigDict

from contract_diff.comparison.enums.change_type import ChangeType
from contract_diff.comparison.models.text_fragment import TextFragment


class ComparedClause(BaseModel):
    """
    Internal comparison result for one aligned clause.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    change_type: ChangeType

    original_clause_id: str | None

    revised_clause_id: str | None

    revised_anchor_clause_id: str | None

    original_text: str | None

    revised_text: str | None

    fragments: tuple[TextFragment, ...]

    heading: str | None = None

    original_page_number: int | None = None

    revised_page_number: int | None = None

    original_source_unit_ids: tuple[str, ...] = ()

    revised_source_unit_ids: tuple[str, ...] = ()

    original_source_span_ids: tuple[str, ...] = ()

    revised_source_span_ids: tuple[str, ...] = ()

    warnings: tuple[str, ...] = ()
