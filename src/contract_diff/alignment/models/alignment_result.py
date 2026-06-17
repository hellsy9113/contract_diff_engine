from pydantic import BaseModel, ConfigDict

from contract_diff.alignment.enums.document_similarity_status import (
    DocumentSimilarityStatus,
)
from contract_diff.alignment.models.aligned_clause import AlignedClause
from contract_diff.alignment.models.document_similarity_result import (
    DocumentSimilarityResult,
)


class AlignmentResult(BaseModel):
    """
    Top-level output consumed by the comparison layer.
    """

    model_config = ConfigDict(frozen=True)

    status: DocumentSimilarityStatus

    document_similarity: DocumentSimilarityResult

    aligned_clauses: tuple[AlignedClause, ...]

    original_only_count: int

    revised_only_count: int

    matched_count: int

    warnings: tuple[str, ...] = ()
