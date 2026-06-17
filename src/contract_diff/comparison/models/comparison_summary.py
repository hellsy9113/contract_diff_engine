from pydantic import BaseModel, ConfigDict


class ComparisonSummary(BaseModel):
    """
    Internal counts of comparison change types.
    """

    model_config = ConfigDict(frozen=True)

    total: int

    unchanged: int

    modified: int

    added: int

    removed: int
