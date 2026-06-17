from typing import Literal

from pydantic import BaseModel, ConfigDict

AnchorType = Literal["revised_clause", "revised_anchor_clause"]


class AnnotationTarget(BaseModel):
    """
    Revised-document location where an annotation should attach.
    """

    model_config = ConfigDict(frozen=True)

    clause_id: str

    page_number: int

    source_span_ids: tuple[str, ...]

    anchor_type: AnchorType
