from pydantic import BaseModel, ConfigDict

from contract_diff.alignment.enums.alignment_status import AlignmentStatus
from contract_diff.alignment.models.alignment_score import AlignmentScore


class AlignedClause(BaseModel):
    """
    One deterministic clause alignment decision.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    status: AlignmentStatus

    original_clause_id: str | None

    revised_clause_id: str | None

    revised_anchor_clause_id: str | None

    score: AlignmentScore

    reason: str

    warnings: tuple[str, ...] = ()
