from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from contract_diff.v3.models.debug import V3DebugInfo
from contract_diff.v3.models.diff import V3ClauseStatus, V3DiffToken


class V3ClauseDiff(BaseModel):
    """Final frontend-facing diff for one aligned clause."""

    model_config = ConfigDict(frozen=True)

    id: str
    number: str | None = None
    heading: str | None = None
    status: V3ClauseStatus
    original_text: str | None = None
    revised_text: str | None = None
    diff_tokens: list[V3DiffToken]
    page_number_original: int | None = None
    page_number_revised: int | None = None
    order_index: int


class V3CompareSummary(BaseModel):
    """Summary counts for a v3 clause comparison response."""

    model_config = ConfigDict(frozen=True)

    total_clauses: int
    unchanged_clauses: int
    changed_clauses: int
    added_clauses: int
    deleted_clauses: int
    modified_clauses: int


class V3ClauseCompareResponse(BaseModel):
    """JSON-only v3 clause comparison response."""

    model_config = ConfigDict(frozen=True)

    version: Literal["v3"] = "v3"
    document_title: str | None = None
    summary: V3CompareSummary
    clauses: list[V3ClauseDiff]
    debug: V3DebugInfo | None = None
