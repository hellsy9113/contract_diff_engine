from pydantic import BaseModel, ConfigDict


class RenderedDocument(BaseModel):
    """
    Final rendered PDF payload returned by the engine.
    """

    model_config = ConfigDict(frozen=True)

    filename: str

    content_type: str = "application/pdf"

    data: bytes

    warnings: tuple[str, ...] = ()
