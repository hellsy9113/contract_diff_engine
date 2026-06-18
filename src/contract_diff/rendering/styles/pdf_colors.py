from dataclasses import dataclass

from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.enums.highlight_style import HighlightStyle

PdfColor = tuple[float, float, float]

BLACK: PdfColor = (0.0, 0.0, 0.0)
ADDED_HIGHLIGHT_COLOR: PdfColor = (0.55, 0.90, 0.55)
MODIFIED_HIGHLIGHT_COLOR: PdfColor = (1.0, 0.82, 0.35)
DELETED_MARKER_COLOR: PdfColor = (1.0, 0.35, 0.35)
UNCERTAIN_HIGHLIGHT_COLOR: PdfColor = (0.65, 0.75, 1.0)

GREEN = ADDED_HIGHLIGHT_COLOR
RED = DELETED_MARKER_COLOR
YELLOW = MODIFIED_HIGHLIGHT_COLOR

HIGHLIGHT_OPACITY = 0.28
DELETION_MARKER_OPACITY = 0.60
MAX_HIGHLIGHT_RECTS_PER_CHANGE = 6
MAX_HIGHLIGHTED_AREA_RATIO_PER_PAGE = 0.18
MIN_FRAGMENT_LENGTH = 8


@dataclass(frozen=True)
class AnnotationStyle:
    color: PdfColor
    opacity: float
    max_rects: int = MAX_HIGHLIGHT_RECTS_PER_CHANGE


def color_for_style(style: HighlightStyle) -> PdfColor:
    if style is HighlightStyle.MODIFIED_HIGHLIGHT:
        return MODIFIED_HIGHLIGHT_COLOR

    if style is HighlightStyle.ADDED_HIGHLIGHT:
        return ADDED_HIGHLIGHT_COLOR

    return DELETED_MARKER_COLOR


def style_for_annotation_type(annotation_type: AnnotationType) -> AnnotationStyle:
    if annotation_type is AnnotationType.ADDED:
        return AnnotationStyle(
            color=ADDED_HIGHLIGHT_COLOR,
            opacity=HIGHLIGHT_OPACITY,
        )

    if annotation_type is AnnotationType.MODIFIED:
        return AnnotationStyle(
            color=MODIFIED_HIGHLIGHT_COLOR,
            opacity=HIGHLIGHT_OPACITY,
        )

    if annotation_type is AnnotationType.REMOVED:
        return AnnotationStyle(
            color=DELETED_MARKER_COLOR,
            opacity=DELETION_MARKER_OPACITY,
            max_rects=1,
        )

    return AnnotationStyle(
        color=UNCERTAIN_HIGHLIGHT_COLOR,
        opacity=HIGHLIGHT_OPACITY,
    )


def style_for_highlight_style(style: HighlightStyle) -> AnnotationStyle:
    if style is HighlightStyle.ADDED_HIGHLIGHT:
        return AnnotationStyle(
            color=ADDED_HIGHLIGHT_COLOR,
            opacity=HIGHLIGHT_OPACITY,
        )

    if style is HighlightStyle.MODIFIED_HIGHLIGHT:
        return AnnotationStyle(
            color=MODIFIED_HIGHLIGHT_COLOR,
            opacity=HIGHLIGHT_OPACITY,
        )

    return AnnotationStyle(
        color=DELETED_MARKER_COLOR,
        opacity=DELETION_MARKER_OPACITY,
        max_rects=1,
    )
