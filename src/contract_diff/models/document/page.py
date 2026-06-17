from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from contract_diff.models.document.block import Block
from contract_diff.models.document.bounding_box import BoundingBox


class Page(BaseModel):
    """
    Represents one extracted page and its layout tree.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    page_number: int

    bbox: BoundingBox | None = None

    blocks: tuple[Block, ...]

    @property
    def text(self) -> str:
        return "\n".join(block.text for block in self.blocks)
