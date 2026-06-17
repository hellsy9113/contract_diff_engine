from pydantic import BaseModel, ConfigDict

from contract_diff.alignment.enums.document_similarity_status import (
    DocumentSimilarityStatus,
)


class DocumentSimilarityResult(BaseModel):
    """
    Frontend-safe output from the document similarity gate.
    """

    model_config = ConfigDict(frozen=True)

    status: DocumentSimilarityStatus

    overall_score: float

    minimum_required_score: float

    heading_score: float

    clause_text_score: float

    clause_count_score: float

    document_length_score: float

    reason: str | None = None

    message: str | None = None

    warnings: tuple[str, ...] = ()
