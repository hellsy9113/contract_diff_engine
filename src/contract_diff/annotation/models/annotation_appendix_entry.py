from pydantic import BaseModel, ConfigDict

from contract_diff.annotation.enums.annotation_type import AnnotationType


class AnnotationAppendixEntry(BaseModel):
    """
    Metadata entry for an annotation appendix in the rendered PDF.
    """

    model_config = ConfigDict(frozen=True)

    annotation_id: str

    annotation_type: AnnotationType

    page_number: int | None

    heading: str | None = None

    original_text: str | None = None

    revised_text: str | None = None

    notes: tuple[str, ...] = ()
