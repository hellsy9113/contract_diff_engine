from __future__ import annotations

import re
from typing import Any, cast

import fitz  # type: ignore[import-untyped]

from contract_diff.comparison.structured_changes import Change, Location
from contract_diff.comparison.utils.text_diff_helpers import normalize_for_alignment
from contract_diff.extraction.structured.models import BoundingBox
from contract_diff.rendering.styles.v2 import (
    MAX_HIGHLIGHTS_PER_PAGE,
    MIN_RENDER_FRAGMENT_LENGTH,
    style_for_change_type,
)
from contract_diff.rendering.utils.pdf_rects import (
    dedupe_rects,
    merge_nearby_rects,
    rects_are_similar,
    shrink_rect_vertically,
)
from contract_diff.rendering.utils.visual_fragments import prepare_visual_fragments

_WORD_RE = re.compile(r"[A-Za-z0-9$%]+(?:['’][A-Za-z0-9]+)?")
_NUMERIC_RE = re.compile(r"\d")


def render_changes_to_pdf(base_pdf_bytes: bytes, changes: list[Change]) -> bytes:
    """Render structured changes onto the supplied PDF bytes."""

    document = fitz.open(stream=base_pdf_bytes, filetype="pdf")

    try:
        page_highlight_counts: dict[int, int] = {}

        for change in changes:
            if change.change_type == "deleted":
                _render_deleted_change(document, change)
                continue

            _render_revised_side_change(document, change, page_highlight_counts)

        return cast(bytes, document.tobytes())
    finally:
        document.close()


def _render_revised_side_change(
    document: Any,
    change: Change,
    page_highlight_counts: dict[int, int],
) -> None:
    location = change.revised_location

    if location is None:
        return

    page = _page(document, location.page_index)

    if page is None:
        return

    style = style_for_change_type(change.change_type)
    search_fragments = _search_fragments_for_change(change)

    if not search_fragments:
        return

    target_rect = _target_rect(location)
    rects: list[fitz.Rect] = []

    for fragment in search_fragments:
        for rect in _search_fragment_rects(page, fragment, target_rect):
            if any(rects_are_similar(rect, existing) for existing in rects):
                continue

            rects.append(rect)

            if len(rects) >= style.max_rects:
                break

        if len(rects) >= style.max_rects:
            break

    if not rects:
        return

    page_number = location.page_index + 1

    if page_highlight_counts.get(page_number, 0) >= MAX_HIGHLIGHTS_PER_PAGE:
        return

    if change.change_type == "uncertain":
        annotation = page.add_underline_annot(rects)
    else:
        annotation = page.add_highlight_annot(rects)
        page_highlight_counts[page_number] = page_highlight_counts.get(
            page_number, 0
        ) + 1

    annotation.set_colors(stroke=style.color)
    annotation.set_opacity(style.opacity)
    annotation.set_info(
        title=change.change_id,
        content=_annotation_content(change),
    )
    annotation.update()


def _render_deleted_change(document: Any, change: Change) -> None:
    """Render deletion metadata only, or a small underline near revised anchor."""

    location = change.revised_location

    if location is None or location.bbox is None:
        return

    page = _page(document, location.page_index)

    if page is None:
        return

    style = style_for_change_type(change.change_type)
    bbox = location.bbox
    marker_rect = fitz.Rect(
        max(0.0, bbox.x0 - 18.0),
        bbox.y0,
        max(1.0, bbox.x0 - 6.0),
        bbox.y1,
    )
    annotation = page.add_underline_annot(marker_rect)
    annotation.set_colors(stroke=style.color)
    annotation.set_opacity(style.opacity)
    annotation.set_info(
        title=change.change_id,
        content=_annotation_content(change),
    )
    annotation.update()


def _search_fragments_for_change(change: Change) -> tuple[str, ...]:
    candidates: list[str] = []

    if change.change_type == "added" and change.revised_text:
        candidates.append(change.revised_text)
    elif change.change_type in {"modified", "uncertain"}:
        candidates.extend(change.changed_fragments)

        if (
            not candidates
            and change.revised_text is not None
            and change.confidence >= 0.9
        ):
            candidates.append(change.revised_text)

    fragments: list[str] = []

    for candidate in candidates:
        fragments.extend(_prepare_search_fragments(candidate))

    return tuple(_unique(fragments))


def _prepare_search_fragments(text: str) -> list[str]:
    cleaned = _clean_fragment(text)

    if not cleaned:
        return []

    fragments: list[str] = []

    if _is_meaningful_fragment(cleaned):
        fragments.append(cleaned)

    fragments.extend(prepare_visual_fragments(cleaned))

    return _unique(fragments)


def _search_fragment_rects(
    page: Any,
    fragment: str,
    target_rect: fitz.Rect | None,
) -> list[fitz.Rect]:
    rects = [
        shrink_rect_vertically(rect)
        for rect in page.search_for(fragment)
        if target_rect is None or rect.intersects(target_rect)
    ]
    return merge_nearby_rects(dedupe_rects(rects))


def _target_rect(location: Location) -> fitz.Rect | None:
    if location.bbox is None:
        return None

    return _rect(location.bbox)


def _rect(bbox: BoundingBox) -> fitz.Rect:
    return fitz.Rect(bbox.x0, bbox.y0, bbox.x1, bbox.y1)


def _page(document: Any, page_index: int) -> Any | None:
    if page_index < 0 or page_index >= document.page_count:
        return None

    return document[page_index]


def _annotation_content(change: Change) -> str:
    label = change.change_type.replace("_", " ").title()
    text = change.revised_text or change.original_text or ""
    text = " ".join(text.split())

    if len(text) > 140:
        text = f"{text[:137]}..."

    return f"{label}: {text}" if text else label


def _clean_fragment(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().strip(".,;:!? ")


def _is_meaningful_fragment(fragment: str) -> bool:
    words = _WORD_RE.findall(fragment)

    if not words:
        return False

    if _NUMERIC_RE.search(fragment):
        return True

    if len(fragment) < MIN_RENDER_FRAGMENT_LENGTH:
        return False

    return len(words) <= 8


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_items: list[str] = []

    for item in items:
        key = normalize_for_alignment(item)

        if key in seen:
            continue

        seen.add(key)
        unique_items.append(item)

    return unique_items
