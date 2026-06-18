from __future__ import annotations

from collections import Counter
from typing import Any, cast

import fitz  # type: ignore[import-untyped]

from contract_diff.extraction.structured.models import PdfIntakeReport

LOW_TEXT_CHARS_PER_PAGE = 80
NORMAL_TEXT_CHARS_PER_PAGE = 500
LOW_WORDS_PER_PAGE = 15
TABLE_SHORT_LINE_RATIO_THRESHOLD = 0.45
TABLE_REPEATED_X_THRESHOLD = 0.35
COLUMN_CLUSTER_GAP = 90.0


def profile_pdf(pdf_bytes: bytes) -> PdfIntakeReport:
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        return _invalid_report(f"PDF could not be opened: {exc}")

    with document:
        page_count = int(document.page_count)
        is_encrypted = bool(getattr(document, "needs_pass", False))

        if is_encrypted:
            return _encrypted_report(page_count)

        warnings: list[str] = []
        text_char_count = 0
        word_count = 0
        image_count = 0
        annotation_count = 0
        highlight_annotation_count = 0
        short_line_count = 0
        line_count = 0
        repeated_x_score_total = 0.0
        drawing_count = 0
        column_page_scores: list[float] = []

        for page_index in range(page_count):
            try:
                page = document[page_index]
                text = page.get_text()
                text_char_count += len(text.strip())
                word_count += len(text.split())
                image_count += len(page.get_images(full=True))
                page_annotation_count, page_highlight_count = _count_annotations(page)
                annotation_count += page_annotation_count
                highlight_annotation_count += page_highlight_count

                text_dict = cast(dict[str, Any], page.get_text("dict"))
                page_lines, page_short_lines, page_x_positions = _line_metrics(
                    text_dict
                )
                line_count += page_lines
                short_line_count += page_short_lines
                repeated_x_score_total += _repeated_x_score(page_x_positions)
                drawing_count += _drawing_count(page)
                column_page_scores.append(_page_column_likelihood(text_dict))
            except Exception as exc:
                warnings.append(f"Page {page_index + 1} could not be profiled: {exc}")

        table_likelihood = _table_likelihood(
            line_count=line_count,
            short_line_count=short_line_count,
            repeated_x_score_total=repeated_x_score_total,
            drawing_count=drawing_count,
            page_count=page_count,
        )
        column_likelihood = _average(column_page_scores)
        scanned_likelihood = _scanned_likelihood(
            page_count=page_count,
            text_char_count=text_char_count,
            word_count=word_count,
            image_count=image_count,
        )
        warnings.extend(
            _quality_warnings(
                page_count=page_count,
                text_char_count=text_char_count,
                word_count=word_count,
                annotation_count=annotation_count,
                table_likelihood=table_likelihood,
                column_likelihood=column_likelihood,
                scanned_likelihood=scanned_likelihood,
            )
        )

        return PdfIntakeReport(
            is_valid_pdf=True,
            page_count=page_count,
            is_encrypted=False,
            has_extractable_text=text_char_count > 0,
            text_char_count=text_char_count,
            word_count=word_count,
            image_count=image_count,
            annotation_count=annotation_count,
            highlight_annotation_count=highlight_annotation_count,
            table_likelihood=table_likelihood,
            column_likelihood=column_likelihood,
            scanned_likelihood=scanned_likelihood,
            warnings=warnings,
        )


def _invalid_report(warning: str) -> PdfIntakeReport:
    return PdfIntakeReport(
        is_valid_pdf=False,
        page_count=0,
        is_encrypted=False,
        has_extractable_text=False,
        text_char_count=0,
        word_count=0,
        image_count=0,
        annotation_count=0,
        highlight_annotation_count=0,
        table_likelihood=0.0,
        column_likelihood=0.0,
        scanned_likelihood=0.0,
        warnings=[warning],
    )


def _encrypted_report(page_count: int) -> PdfIntakeReport:
    return PdfIntakeReport(
        is_valid_pdf=True,
        page_count=page_count,
        is_encrypted=True,
        has_extractable_text=False,
        text_char_count=0,
        word_count=0,
        image_count=0,
        annotation_count=0,
        highlight_annotation_count=0,
        table_likelihood=0.0,
        column_likelihood=0.0,
        scanned_likelihood=0.0,
        warnings=["PDF is encrypted and cannot be profiled without a password"],
    )


def _count_annotations(page: Any) -> tuple[int, int]:
    annotation = page.first_annot
    annotation_count = 0
    highlight_count = 0

    while annotation is not None:
        annotation_count += 1

        if annotation.type[1] == "Highlight":
            highlight_count += 1

        annotation = annotation.next

    return annotation_count, highlight_count


def _line_metrics(text_dict: dict[str, Any]) -> tuple[int, int, list[float]]:
    line_count = 0
    short_line_count = 0
    x_positions: list[float] = []

    for raw_block in text_dict.get("blocks", []):
        block = cast(dict[str, Any], raw_block)

        if block.get("type") != 0:
            continue

        block_bbox = block.get("bbox")

        if isinstance(block_bbox, (tuple, list)) and len(block_bbox) == 4:
            x_positions.append(round(float(block_bbox[0]) / 10.0) * 10.0)

        for raw_line in block.get("lines", []):
            line = cast(dict[str, Any], raw_line)
            text = _line_text(line)

            if not text:
                continue

            line_count += 1

            # Table-like PDFs often have many tiny cells or wrapped fragments.
            if len(text) <= 28:
                short_line_count += 1

    return line_count, short_line_count, x_positions


def _line_text(line: dict[str, Any]) -> str:
    spans = line.get("spans", [])
    parts = [
        str(cast(dict[str, Any], span).get("text", ""))
        for span in spans
        if isinstance(span, dict)
    ]
    return "".join(parts).strip()


def _repeated_x_score(x_positions: list[float]) -> float:
    if not x_positions:
        return 0.0

    counts = Counter(x_positions)

    if len(counts) < 2:
        return 0.0

    repeated = sum(count for count in counts.values() if count >= 3)
    return repeated / len(x_positions)


def _drawing_count(page: Any) -> int:
    try:
        return len(page.get_drawings())
    except Exception:
        return 0


def _table_likelihood(
    line_count: int,
    short_line_count: int,
    repeated_x_score_total: float,
    drawing_count: int,
    page_count: int,
) -> float:
    if line_count == 0:
        return 0.0

    # Heuristic score: short repeated lines and stable x positions are common in
    # table extracts; many PDF drawing primitives add a smaller signal.
    short_line_score = short_line_count / line_count
    repeated_x_score = repeated_x_score_total / max(1, page_count)
    drawing_score = min(1.0, drawing_count / max(1, page_count * 20))
    weighted = (
        (short_line_score / TABLE_SHORT_LINE_RATIO_THRESHOLD) * 0.45
        + (repeated_x_score / TABLE_REPEATED_X_THRESHOLD) * 0.4
        + drawing_score * 0.15
    )
    return _clamp(weighted)


def _page_column_likelihood(text_dict: dict[str, Any]) -> float:
    x_positions: list[float] = []

    for raw_block in text_dict.get("blocks", []):
        block = cast(dict[str, Any], raw_block)

        if block.get("type") != 0:
            continue

        text = _block_text(block)

        bbox = block.get("bbox")

        if text and isinstance(bbox, (tuple, list)) and len(bbox) == 4:
            x_positions.append(float(bbox[0]))

        for raw_line in block.get("lines", []):
            line = cast(dict[str, Any], raw_line)
            line_text = _line_text(line)
            line_bbox = line.get("bbox")

            if (
                line_text
                and isinstance(line_bbox, (tuple, list))
                and len(line_bbox) == 4
            ):
                x_positions.append(float(line_bbox[0]))

    if len(x_positions) < 4:
        return 0.0

    ordered_positions = sorted(x_positions)
    gaps = [
        (right - left, left, right)
        for left, right in zip(ordered_positions, ordered_positions[1:])
    ]
    significant_gaps = [gap for gap in gaps if gap[0] >= COLUMN_CLUSTER_GAP]

    if not significant_gaps:
        return 0.0

    largest_gap, gap_left, gap_right = max(significant_gaps)
    split_x = (gap_left + gap_right) / 2.0
    left_count = sum(1 for x in ordered_positions if x <= split_x)
    balance = min(left_count, len(ordered_positions) - left_count) / len(
        ordered_positions
    )
    gap_score = min(1.0, largest_gap / 180.0)
    return _clamp(gap_score * 0.7 + balance * 0.6)


def _block_text(block: dict[str, Any]) -> str:
    lines = block.get("lines", [])
    return " ".join(
        _line_text(cast(dict[str, Any], line))
        for line in lines
        if isinstance(line, dict)
    ).strip()


def _scanned_likelihood(
    page_count: int,
    text_char_count: int,
    word_count: int,
    image_count: int,
) -> float:
    if page_count <= 0:
        return 0.0

    chars_per_page = text_char_count / page_count
    words_per_page = word_count / page_count
    images_per_page = image_count / page_count

    if images_per_page <= 0:
        return 0.0

    if chars_per_page >= NORMAL_TEXT_CHARS_PER_PAGE and words_per_page >= 80:
        return 0.0

    low_text_score = 1.0 - min(1.0, chars_per_page / LOW_TEXT_CHARS_PER_PAGE)
    low_word_score = 1.0 - min(1.0, words_per_page / LOW_WORDS_PER_PAGE)
    image_score = min(1.0, images_per_page)

    # Image-heavy pages with almost no text are the core scanned-PDF signal.
    return _clamp(low_text_score * 0.45 + low_word_score * 0.25 + image_score * 0.3)


def _quality_warnings(
    page_count: int,
    text_char_count: int,
    word_count: int,
    annotation_count: int,
    table_likelihood: float,
    column_likelihood: float,
    scanned_likelihood: float,
) -> list[str]:
    warnings: list[str] = []

    if scanned_likelihood >= 0.65:
        warnings.append("PDF appears scanned or image-heavy")

    if page_count > 0 and (
        text_char_count < page_count * LOW_TEXT_CHARS_PER_PAGE
        or word_count < page_count * LOW_WORDS_PER_PAGE
    ):
        warnings.append("PDF has very little extractable text")

    if annotation_count > 0:
        warnings.append("PDF has existing annotations")

    if table_likelihood >= 0.55:
        warnings.append("PDF may contain tables")

    if column_likelihood >= 0.55:
        warnings.append("PDF may contain multiple columns")

    return warnings


def _average(values: list[float]) -> float:
    if not values:
        return 0.0

    return _clamp(sum(values) / len(values))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
