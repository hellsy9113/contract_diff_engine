from pydantic import BaseModel, ConfigDict

from contract_diff.core.models.engine_status import EngineStatus
from contract_diff.rendering.models.rendered_document import RenderedDocument


class EngineResult(BaseModel):
    """
    Controlled output from the core comparison engine.
    """

    model_config = ConfigDict(frozen=True)

    status: EngineStatus

    rendered_document: RenderedDocument | None = None

    rejection_reason: str | None = None

    message: str | None = None

    similarity_score: float | None = None

    warnings: tuple[str, ...] = ()
