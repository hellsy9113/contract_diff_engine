from pydantic import BaseModel, ConfigDict


class AlignmentScore(BaseModel):
    """
    Clause alignment score breakdown.
    """

    model_config = ConfigDict(frozen=True)

    overall: float

    clause_number_score: float

    heading_score: float

    section_score: float

    text_score: float

    position_score: float
