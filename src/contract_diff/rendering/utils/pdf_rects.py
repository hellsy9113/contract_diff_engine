from __future__ import annotations

import fitz  # type: ignore[import-untyped]


def rects_are_similar(
    a: fitz.Rect,
    b: fitz.Rect,
    tolerance: float = 2.0,
) -> bool:
    return (
        abs(float(a.x0) - float(b.x0)) <= tolerance
        and abs(float(a.y0) - float(b.y0)) <= tolerance
        and abs(float(a.x1) - float(b.x1)) <= tolerance
        and abs(float(a.y1) - float(b.y1)) <= tolerance
    )


def dedupe_rects(rects: list[fitz.Rect]) -> list[fitz.Rect]:
    deduped: list[fitz.Rect] = []

    for rect in rects:
        if any(rects_are_similar(rect, existing) for existing in deduped):
            continue

        deduped.append(rect)

    return deduped


def merge_nearby_rects(
    rects: list[fitz.Rect],
    x_gap_tolerance: float = 2.0,
    y_tolerance: float = 2.0,
) -> list[fitz.Rect]:
    if not rects:
        return []

    sorted_rects = sorted(rects, key=lambda rect: (float(rect.y0), float(rect.x0)))
    merged: list[fitz.Rect] = [fitz.Rect(sorted_rects[0])]

    for rect in sorted_rects[1:]:
        current = merged[-1]

        if _same_line(current, rect, y_tolerance) and (
            float(rect.x0) - float(current.x1) <= x_gap_tolerance
        ):
            current.include_rect(rect)
            continue

        merged.append(fitz.Rect(rect))

    return merged


def shrink_rect_vertically(rect: fitz.Rect, amount: float = 0.75) -> fitz.Rect:
    if float(rect.height) <= amount * 3:
        return fitz.Rect(rect)

    return fitz.Rect(rect.x0, rect.y0 + amount, rect.x1, rect.y1 - amount)


def rect_area(rect: fitz.Rect) -> float:
    return max(0.0, float(rect.width)) * max(0.0, float(rect.height))


def _same_line(a: fitz.Rect, b: fitz.Rect, tolerance: float) -> bool:
    return (
        abs(float(a.y0) - float(b.y0)) <= tolerance
        and abs(float(a.y1) - float(b.y1)) <= tolerance
    )
