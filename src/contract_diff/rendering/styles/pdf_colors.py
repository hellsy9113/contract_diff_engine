from contract_diff.annotation.enums.highlight_style import HighlightStyle

PdfColor = tuple[float, float, float]

BLACK: PdfColor = (0.0, 0.0, 0.0)
GREEN: PdfColor = (0.25, 0.78, 0.42)
RED: PdfColor = (0.9, 0.12, 0.12)
YELLOW: PdfColor = (1.0, 0.92, 0.25)


def color_for_style(style: HighlightStyle) -> PdfColor:
    if style is HighlightStyle.MODIFIED_HIGHLIGHT:
        return YELLOW

    if style is HighlightStyle.ADDED_HIGHLIGHT:
        return GREEN

    return RED
