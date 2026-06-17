from pydantic import BaseModel, ConfigDict

from contract_diff.normalization.models.normalized_text_unit import (
    NormalizedTextUnit,
)


class NormalizedPage(BaseModel):
    """
    Normalized text units for a single source page.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    page_number: int

    source_page_id: str

    units: tuple[NormalizedTextUnit, ...]

    @property
    def text(self) -> str:
        return "\n".join(unit.text for unit in self.units)
