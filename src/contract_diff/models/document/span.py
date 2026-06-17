from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from contract_diff.models.document.bounding_box import BoundingBox


class Span(BaseModel):
    """
    Contiguous run of text with shared visual styling.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    text: str

    bbox: BoundingBox | None = None

    font: str | None = None

    font_size: float | None = None

    flags: int | None = None
