from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class BoundingBox(BaseModel):
    """
    Rectangle in document/page coordinate space.
    """

    model_config = ConfigDict(frozen=True)

    x0: float
    y0: float
    x1: float
    y1: float

    @model_validator(mode="after")
    def validate_coordinate_order(self) -> Self:
        if self.x1 < self.x0:
            raise ValueError("x1 must be greater than or equal to x0.")

        if self.y1 < self.y0:
            raise ValueError("y1 must be greater than or equal to y0.")

        return self
