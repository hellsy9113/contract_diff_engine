from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class V3PageText(BaseModel):
    """Plain text extracted from one document page for the v3 JSON pipeline."""

    model_config = ConfigDict(frozen=True)

    page_number: int
    text: str


class V3DocumentText(BaseModel):
    """Read-only document text input for v3 clause extraction."""

    model_config = ConfigDict(frozen=True)

    title: str | None = None
    full_text: str
    pages: list[V3PageText]
