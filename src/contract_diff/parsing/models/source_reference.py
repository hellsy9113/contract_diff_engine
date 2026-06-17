from pydantic import BaseModel, ConfigDict

from contract_diff.normalization.models.normalized_text_unit import (
    NormalizedTextUnit,
)


class SourceReference(BaseModel):
    """
    Traceability back to normalized units and extracted spans.
    """

    model_config = ConfigDict(frozen=True)

    page_number: int

    source_unit_ids: tuple[str, ...]

    source_page_ids: tuple[str, ...]

    source_block_ids: tuple[str, ...]

    source_line_ids: tuple[str, ...]

    source_span_ids: tuple[str, ...]

    @classmethod
    def from_unit(cls, unit: NormalizedTextUnit) -> "SourceReference":
        return cls(
            page_number=unit.page_number,
            source_unit_ids=(unit.id,),
            source_page_ids=(unit.source_page_id,),
            source_block_ids=(unit.source_block_id,),
            source_line_ids=unit.source_line_ids,
            source_span_ids=unit.source_span_ids,
        )
