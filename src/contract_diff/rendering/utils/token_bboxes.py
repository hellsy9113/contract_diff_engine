from __future__ import annotations

from collections import defaultdict

import fitz  # type: ignore[import-untyped]

from contract_diff.extraction.structured.models import WordToken

TOKEN_BBOX_PADDING = 1.25
HORIZONTAL_MERGE_GAP = 4.0


def group_changed_token_bboxes(tokens: list[WordToken]) -> list[fitz.Rect]:
    """Group changed token boxes into compact per-line highlight rectangles."""

    grouped_by_page = group_changed_token_bboxes_by_page(tokens)
    rects: list[fitz.Rect] = []

    for page_number in sorted(grouped_by_page):
        rects.extend(grouped_by_page[page_number])

    return rects


def group_changed_token_bboxes_by_page(
    tokens: list[WordToken],
) -> dict[int, list[fitz.Rect]]:
    by_line: dict[tuple[int, str], list[WordToken]] = defaultdict(list)

    for token in tokens:
        by_line[_line_key(token)].append(token)

    grouped: dict[int, list[fitz.Rect]] = defaultdict(list)

    for (page_number, _line_id), line_tokens in by_line.items():
        line_rects = [
            _padded_rect(rect)
            for rect in _merge_line_rects([_token_rect(token) for token in line_tokens])
        ]
        grouped[page_number].extend(line_rects)

    return {
        page_number: sorted(
            rects,
            key=lambda rect: (float(rect.y0), float(rect.x0)),
        )
        for page_number, rects in grouped.items()
    }


def _line_key(token: WordToken) -> tuple[int, str]:
    if token.line_id:
        return (token.page_number, token.line_id)

    return (token.page_number, f"bbox-y-{round(token.bbox[1], 1)}")


def _merge_line_rects(rects: list[fitz.Rect]) -> list[fitz.Rect]:
    if not rects:
        return []

    sorted_rects = sorted(rects, key=lambda rect: (float(rect.x0), float(rect.y0)))
    merged: list[fitz.Rect] = [fitz.Rect(sorted_rects[0])]

    for rect in sorted_rects[1:]:
        current = merged[-1]

        if float(rect.x0) - float(current.x1) <= HORIZONTAL_MERGE_GAP:
            current.include_rect(rect)
            continue

        merged.append(fitz.Rect(rect))

    return merged


def _token_rect(token: WordToken) -> fitz.Rect:
    return fitz.Rect(*token.bbox)


def _padded_rect(rect: fitz.Rect) -> fitz.Rect:
    return fitz.Rect(
        max(0.0, float(rect.x0) - TOKEN_BBOX_PADDING),
        max(0.0, float(rect.y0) - TOKEN_BBOX_PADDING),
        float(rect.x1) + TOKEN_BBOX_PADDING,
        float(rect.y1) + TOKEN_BBOX_PADDING,
    )
