from pydantic import BaseModel, ConfigDict


class V3DebugInfo(BaseModel):
    """Optional debug payload for the v3 clause comparison endpoint."""

    model_config = ConfigDict(frozen=True)

    original_clause_count: int
    revised_clause_count: int
    aligned_clause_count: int
    added_clause_ids: list[str]
    deleted_clause_ids: list[str]
    modified_clause_ids: list[str]
    low_confidence_alignments: list[str]
    suspicious_large_diffs: list[str]
