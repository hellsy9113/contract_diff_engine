from pydantic import BaseModel, ConfigDict

from contract_diff.parsing.enums.numbering_style import NumberingStyle
from contract_diff.parsing.rules.numbering_rules import (
    DECIMAL_CLAUSE_RE,
    LETTER_MARKER_RE,
    ROMAN_MARKER_RE,
    STANDALONE_MARKER_RE,
)


class ClauseNumberMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: str
    body: str
    numbering_style: NumberingStyle


class ClauseNumberDetector:
    """
    Detects clause numbering without interpreting legal meaning.
    """

    @classmethod
    def detect(cls, text: str) -> ClauseNumberMatch | None:
        stripped = text.strip()

        decimal_match = DECIMAL_CLAUSE_RE.match(stripped)
        if decimal_match:
            return ClauseNumberMatch(
                number=decimal_match.group("number"),
                body=decimal_match.group("body").strip(),
                numbering_style=NumberingStyle.NESTED_DECIMAL,
            )

        marker_match = STANDALONE_MARKER_RE.match(stripped)
        if marker_match:
            number = marker_match.group("number")
            return ClauseNumberMatch(
                number=number,
                body=marker_match.group("body").strip(),
                numbering_style=cls._marker_style(number),
            )

        return None

    @classmethod
    def _marker_style(cls, marker: str) -> NumberingStyle:
        if ROMAN_MARKER_RE.match(marker):
            return NumberingStyle.ROMAN

        if LETTER_MARKER_RE.match(marker):
            return NumberingStyle.LETTER

        return NumberingStyle.NONE
