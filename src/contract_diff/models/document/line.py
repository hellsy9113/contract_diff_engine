from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from contract_diff.models.document.bounding_box import BoundingBox
from contract_diff.models.document.span import Span


class Line(BaseModel):
    """
    Text spans that occupy the same visual line.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    bbox: BoundingBox | None = None

    spans: tuple[Span, ...]

    @property
    def text(self) -> str:
        return "".join(span.text for span in self.spans)
