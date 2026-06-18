from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class BoundingBox(BaseModel):
    model_config = ConfigDict(frozen=True)

    x0: float
    y0: float
    x1: float
    y1: float

    @model_validator(mode="after")
    def validate_coordinate_order(self) -> Self:
        if self.x1 < self.x0:
            raise ValueError("x1 must be greater than or equal to x0.")

        if self.y1 < self.y0:
            raise ValueError("y1 must be greater than or equal to y0.")

        return self


class ExtractedWord(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    bbox: BoundingBox
    page_index: int
    word_index: int
    block_index: int | None
    line_index: int | None


class TextSpan(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    bbox: BoundingBox
    font: str | None
    size: float | None
    flags: int | None


class TextLine(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    bbox: BoundingBox
    spans: list[TextSpan]
    line_index: int


class TextBlock(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    normalized_text: str
    page_index: int
    block_index: int
    bbox: BoundingBox
    lines: list[TextLine]
    block_type: str
    column_index: int | None
    section_path: list[str]


class ExtractedPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_index: int
    width: float
    height: float
    text: str
    blocks: list[TextBlock]
    words: list[ExtractedWord]


class StructuredDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_count: int
    text: str
    pages: list[ExtractedPage]
    warnings: list[str]


class PdfIntakeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_valid_pdf: bool
    page_count: int
    is_encrypted: bool
    has_extractable_text: bool
    text_char_count: int
    word_count: int
    image_count: int
    annotation_count: int
    highlight_annotation_count: int
    table_likelihood: float
    column_likelihood: float
    scanned_likelihood: float
    warnings: list[str]
