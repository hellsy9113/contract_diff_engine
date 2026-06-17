from pydantic import BaseModel, ConfigDict

from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.enums.highlight_style import HighlightStyle
from contract_diff.annotation.models.annotation_target import AnnotationTarget
from contract_diff.comparison.models.text_fragment import TextFragment


class AnnotationItem(BaseModel):
    """
    Renderer-facing instruction for one detected contract change.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    annotation_type: AnnotationType

    style: HighlightStyle

    target: AnnotationTarget | None

    original_text: str | None

    revised_text: str | None

    popup_text: str

    heading: str | None = None

    page_number: int | None = None

    fragments: tuple[TextFragment, ...] = ()

    warnings: tuple[str, ...] = ()
