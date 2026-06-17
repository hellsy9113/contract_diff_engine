from pydantic import BaseModel, ConfigDict

from contract_diff.annotation.models.annotation_appendix_entry import (
    AnnotationAppendixEntry,
)
from contract_diff.annotation.models.annotation_item import AnnotationItem


class AnnotationSummary(BaseModel):
    """
    Count summary for the annotation plan.
    """

    model_config = ConfigDict(frozen=True)

    total: int

    modified: int

    added: int

    removed: int

    unresolved: int


class AnnotationPlan(BaseModel):
    """
    Top-level annotation output consumed by the rendering layer.
    """

    model_config = ConfigDict(frozen=True)

    annotations: tuple[AnnotationItem, ...]

    appendix_entries: tuple[AnnotationAppendixEntry, ...]

    summary: AnnotationSummary

    warnings: tuple[str, ...] = ()
