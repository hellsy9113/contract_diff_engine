from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from contract_diff.models.document.bounding_box import BoundingBox
from contract_diff.models.document.line import Line


class Block(BaseModel):
    """
    Layout block containing one or more visual lines.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    bbox: BoundingBox | None = None

    lines: tuple[Line, ...]

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)
