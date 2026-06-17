from pydantic import BaseModel, ConfigDict


class NormalizedTextUnit(BaseModel):
    """
    Cleaned text with references back to source document spans.
    """

    model_config = ConfigDict(frozen=True)

    id: str

    text: str

    page_number: int

    source_page_id: str

    source_block_id: str

    source_line_ids: tuple[str, ...]

    source_span_ids: tuple[str, ...]
