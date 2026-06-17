from pydantic import BaseModel, ConfigDict

from contract_diff.comparison.enums.fragment_operation import FragmentOperation


class TextFragment(BaseModel):
    """
    Word-level text fragment inside a compared clause.
    """

    model_config = ConfigDict(frozen=True)

    operation: FragmentOperation

    sequence_index: int

    text: str | None = None

    original_text: str | None = None

    revised_text: str | None = None
