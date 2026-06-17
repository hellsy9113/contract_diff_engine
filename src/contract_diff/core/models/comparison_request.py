from pydantic import BaseModel, ConfigDict


class ComparisonRequest(BaseModel):
    """
    Binary request payload for the core engine.
    """

    model_config = ConfigDict(frozen=True)

    original_pdf: bytes

    revised_pdf: bytes

    original_filename: str = "original.pdf"

    revised_filename: str = "revised.pdf"
