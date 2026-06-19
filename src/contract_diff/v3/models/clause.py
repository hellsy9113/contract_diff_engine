from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from contract_diff.v3.models.diff import V3ClauseStatus


class V3ExtractedClause(BaseModel):
    """Clause detected from v3 document text."""

    model_config = ConfigDict(frozen=True)

    id: str
    number: str | None = None
    heading: str | None = None
    text: str
    page_number: int | None = None
    order_index: int


class V3ClauseAlignment(BaseModel):
    """Alignment result for one original/revised v3 clause pair."""

    model_config = ConfigDict(frozen=True)

    original_clause: V3ExtractedClause | None = None
    revised_clause: V3ExtractedClause | None = None
    status: V3ClauseStatus
    confidence: float = Field(ge=0.0, le=1.0)
    order_index: int
