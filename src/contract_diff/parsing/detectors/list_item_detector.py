from pydantic import BaseModel, ConfigDict

from contract_diff.parsing.enums.numbering_style import NumberingStyle
from contract_diff.parsing.rules.numbering_rules import (
    BULLET_MARKER_RE,
    LETTER_MARKER_RE,
    ROMAN_MARKER_RE,
)


class ListItemMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    marker: str
    body: str
    numbering_style: NumberingStyle


class ListItemDetector:
    """
    Detects contract list item markers.
    """

    @classmethod
    def detect(cls, text: str) -> ListItemMatch | None:
        stripped = text.strip()
        parts = stripped.split(maxsplit=1)

        if len(parts) != 2:
            return None

        marker, body = parts
        style = cls._marker_style(marker)

        if style is NumberingStyle.NONE:
            return None

        return ListItemMatch(
            marker=marker,
            body=body.strip(),
            numbering_style=style,
        )

    @classmethod
    def _marker_style(cls, marker: str) -> NumberingStyle:
        if BULLET_MARKER_RE.match(marker):
            return NumberingStyle.BULLET

        if ROMAN_MARKER_RE.match(marker):
            return NumberingStyle.ROMAN

        if LETTER_MARKER_RE.match(marker):
            return NumberingStyle.LETTER

        return NumberingStyle.NONE
