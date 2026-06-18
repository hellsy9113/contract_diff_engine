from __future__ import annotations

from dataclasses import dataclass

from contract_diff.rendering.styles.pdf_colors import (
    ADDED_HIGHLIGHT_COLOR,
    DELETED_MARKER_COLOR,
    HIGHLIGHT_OPACITY,
    MODIFIED_HIGHLIGHT_COLOR,
    UNCERTAIN_HIGHLIGHT_COLOR,
)

PdfColor = tuple[float, float, float]

MAX_HIGHLIGHT_RECTS_PER_CHANGE = 6
MAX_HIGHLIGHTS_PER_PAGE = 25
MIN_RENDER_FRAGMENT_LENGTH = 8


@dataclass(frozen=True)
class ChangeRenderStyle:
    color: PdfColor
    opacity: float
    max_rects: int = MAX_HIGHLIGHT_RECTS_PER_CHANGE


def style_for_change_type(change_type: str) -> ChangeRenderStyle:
    if change_type == "added":
        return ChangeRenderStyle(
            color=ADDED_HIGHLIGHT_COLOR,
            opacity=HIGHLIGHT_OPACITY,
        )

    if change_type == "modified":
        return ChangeRenderStyle(
            color=MODIFIED_HIGHLIGHT_COLOR,
            opacity=HIGHLIGHT_OPACITY,
        )

    if change_type == "deleted":
        return ChangeRenderStyle(
            color=DELETED_MARKER_COLOR,
            opacity=HIGHLIGHT_OPACITY,
            max_rects=1,
        )

    return ChangeRenderStyle(
        color=UNCERTAIN_HIGHLIGHT_COLOR,
        opacity=HIGHLIGHT_OPACITY,
    )
