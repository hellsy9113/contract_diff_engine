from pydantic import BaseModel, ConfigDict

from contract_diff.core.models.engine_result import EngineResult
from contract_diff.core.models.engine_status import EngineStatus


class ErrorResponse(BaseModel):
    """
    JSON response for rejected or failed engine results.
    """

    model_config = ConfigDict(frozen=True)

    status: EngineStatus

    reason: str | None = None

    message: str

    similarity_score: float | None = None

    warnings: tuple[str, ...] = ()

    @classmethod
    def from_engine_result(cls, result: EngineResult) -> "ErrorResponse":
        return cls(
            status=result.status,
            reason=result.rejection_reason,
            message=result.message or "Comparison failed.",
            similarity_score=result.similarity_score,
            warnings=result.warnings,
        )
