from pydantic import BaseModel, ConfigDict

from contract_diff.comparison.models.compared_clause import ComparedClause
from contract_diff.comparison.models.comparison_summary import ComparisonSummary


class ComparisonResult(BaseModel):
    """
    Internal output consumed by annotation and rendering layers.
    """

    model_config = ConfigDict(frozen=True)

    compared_clauses: tuple[ComparedClause, ...]

    summary: ComparisonSummary

    warnings: tuple[str, ...] = ()
