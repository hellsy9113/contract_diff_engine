from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class WordToken(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    text: str
    normalized: str
    page_number: int
    bbox: tuple[float, float, float, float]
    line_id: str | None
    block_id: str | None
    paragraph_id: str | None
    section_heading: str | None
    token_index: int


class PageInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_number: int
    page_index: int
    width: float
    height: float
    token_start_index: int | None
    token_end_index: int | None


class DocumentWordStream(BaseModel):
    model_config = ConfigDict(frozen=True)

    tokens: list[WordToken]
    pages: list[PageInfo]
    source_file_name: str | None = None

    def get_token(self, index: int) -> WordToken:
        return self.tokens[index]

    def slice_tokens(self, start: int, end: int) -> list[WordToken]:
        return self.tokens[start:end]

    def slice_text(self, start: int, end: int) -> str:
        return " ".join(token.text for token in self.slice_tokens(start, end)).strip()

    def find_nearest_surviving_anchor(
        self,
        index: int,
        surviving_token_indexes: set[int] | frozenset[int],
        *,
        max_distance: int | None = None,
    ) -> WordToken | None:
        if not self.tokens or not surviving_token_indexes:
            return None

        tokens_by_index = {token.token_index: token for token in self.tokens}

        if index in surviving_token_indexes:
            return tokens_by_index.get(index)

        search_limit = len(self.tokens)
        if max_distance is not None:
            search_limit = min(search_limit, max_distance)

        for distance in range(1, search_limit + 1):
            before_index = index - distance
            after_index = index + distance

            if before_index in surviving_token_indexes:
                return tokens_by_index.get(before_index)

            if after_index in surviving_token_indexes:
                return tokens_by_index.get(after_index)

        return None


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
    word_tokens: list[WordToken] = Field(default_factory=list)


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
