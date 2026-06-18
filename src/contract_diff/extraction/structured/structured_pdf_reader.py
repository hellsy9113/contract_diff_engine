from __future__ import annotations

import re
from typing import Any, cast

import fitz  # type: ignore[import-untyped]

from contract_diff.extraction.exceptions.extraction import InvalidDocumentError
from contract_diff.extraction.structured.models import (
    BoundingBox,
    ExtractedPage,
    ExtractedWord,
    StructuredDocument,
    TextBlock,
    TextLine,
    TextSpan,
)


def extract_structured_pdf(pdf_bytes: bytes) -> StructuredDocument:
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise InvalidDocumentError("PDF document could not be processed.") from exc

    with document:
        if bool(getattr(document, "needs_pass", False)):
            raise InvalidDocumentError("Encrypted PDF documents are not supported.")

        pages: list[ExtractedPage] = []
        warnings: list[str] = []

        for page_index in range(int(document.page_count)):
            page = document[page_index]
            pages.append(_extract_page(page, page_index, warnings))

    text = "\n".join(page.text for page in pages).strip()
    return StructuredDocument(
        page_count=len(pages),
        text=text,
        pages=pages,
        warnings=warnings,
    )


def normalize_for_alignment(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def bbox_from_tuple(value: object) -> BoundingBox:
    if not isinstance(value, (tuple, list)) or len(value) != 4:
        raise ValueError("Expected a 4-value PDF bounding box.")

    return BoundingBox(
        x0=float(value[0]),
        y0=float(value[1]),
        x1=float(value[2]),
        y1=float(value[3]),
    )


def merge_bboxes(bboxes: list[BoundingBox]) -> BoundingBox:
    if not bboxes:
        raise ValueError("Cannot merge an empty list of bounding boxes.")

    return BoundingBox(
        x0=min(bbox.x0 for bbox in bboxes),
        y0=min(bbox.y0 for bbox in bboxes),
        x1=max(bbox.x1 for bbox in bboxes),
        y1=max(bbox.y1 for bbox in bboxes),
    )


def _extract_page(
    page: Any,
    page_index: int,
    warnings: list[str],
) -> ExtractedPage:
    page_text = str(page.get_text())
    text_dict = cast(dict[str, Any], page.get_text("dict"))
    blocks = _extract_blocks(text_dict, page_index, warnings)
    words = _extract_words(page, page_index, warnings)
    rect = page.rect

    return ExtractedPage(
        page_index=page_index,
        width=float(rect.width),
        height=float(rect.height),
        text=page_text,
        blocks=blocks,
        words=words,
    )


def _extract_blocks(
    text_dict: dict[str, Any],
    page_index: int,
    warnings: list[str],
) -> list[TextBlock]:
    blocks: list[TextBlock] = []

    for raw_block in text_dict.get("blocks", []):
        block_data = cast(dict[str, Any], raw_block)

        if block_data.get("type") != 0:
            continue

        lines = _extract_lines(block_data, warnings)

        if not lines:
            continue

        text = "\n".join(line.text for line in lines).strip()
        normalized_text = normalize_for_alignment(text)

        if not normalized_text:
            continue

        block_bbox = _best_bbox(block_data.get("bbox"), [line.bbox for line in lines])
        blocks.append(
            TextBlock(
                text=text,
                normalized_text=normalized_text,
                page_index=page_index,
                block_index=len(blocks),
                bbox=block_bbox,
                lines=lines,
                block_type="unknown",
                column_index=None,
                section_path=[],
            )
        )

    return blocks


def _extract_lines(
    block_data: dict[str, Any],
    warnings: list[str],
) -> list[TextLine]:
    lines: list[TextLine] = []

    for raw_line in block_data.get("lines", []):
        line_data = cast(dict[str, Any], raw_line)
        spans = _extract_spans(line_data, warnings)

        if not spans:
            continue

        text = "".join(span.text for span in spans).strip()

        if not text:
            continue

        line_bbox = _best_bbox(line_data.get("bbox"), [span.bbox for span in spans])
        lines.append(
            TextLine(
                text=text,
                bbox=line_bbox,
                spans=spans,
                line_index=len(lines),
            )
        )

    return lines


def _extract_spans(
    line_data: dict[str, Any],
    warnings: list[str],
) -> list[TextSpan]:
    spans: list[TextSpan] = []

    for raw_span in line_data.get("spans", []):
        span_data = cast(dict[str, Any], raw_span)
        text = str(span_data.get("text", ""))

        if not text:
            continue

        try:
            bbox = bbox_from_tuple(span_data.get("bbox"))
        except ValueError as exc:
            warnings.append(f"Skipped span with invalid bbox: {exc}")
            continue

        spans.append(
            TextSpan(
                text=text,
                bbox=bbox,
                font=_optional_str(span_data.get("font")),
                size=_optional_float(span_data.get("size")),
                flags=_optional_int(span_data.get("flags")),
            )
        )

    return spans


def _extract_words(
    page: Any,
    page_index: int,
    warnings: list[str],
) -> list[ExtractedWord]:
    words: list[ExtractedWord] = []

    try:
        raw_words = page.get_text("words")
    except Exception as exc:
        warnings.append(f"Page {page_index + 1} words could not be extracted: {exc}")
        return words

    for raw_word in raw_words:
        if not isinstance(raw_word, (tuple, list)) or len(raw_word) < 5:
            continue

        text = str(raw_word[4]).strip()

        if not text:
            continue

        try:
            bbox = bbox_from_tuple(raw_word[:4])
        except ValueError as exc:
            warnings.append(f"Skipped word with invalid bbox: {exc}")
            continue

        words.append(
            ExtractedWord(
                text=text,
                bbox=bbox,
                page_index=page_index,
                word_index=len(words),
                block_index=_optional_int(raw_word[5]) if len(raw_word) > 5 else None,
                line_index=_optional_int(raw_word[6]) if len(raw_word) > 6 else None,
            )
        )

    return words


def _best_bbox(value: object, fallback_bboxes: list[BoundingBox]) -> BoundingBox:
    try:
        return bbox_from_tuple(value)
    except ValueError:
        return merge_bboxes(fallback_bboxes)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None

    return str(value)


def _optional_float(value: object) -> float | None:
    if value is None or not isinstance(value, (int, float, str)):
        return None

    return float(value)


def _optional_int(value: object) -> int | None:
    if value is None or not isinstance(value, (int, float, str)):
        return None

    return int(value)
