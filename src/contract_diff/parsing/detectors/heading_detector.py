from pydantic import BaseModel, ConfigDict

from contract_diff.parsing.enums.numbering_style import NumberingStyle
from contract_diff.parsing.rules.heading_rules import (
    ARTICLE_HEADING_RE,
    NUMBERED_HEADING_RE,
    SECTION_HEADING_RE,
)


class HeadingMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    number: str | None
    title: str
    level: int
    numbering_style: NumberingStyle


class HeadingDetector:
    """
    Detects visible section/article headings using deterministic rules.
    """

    @classmethod
    def detect(cls, text: str) -> HeadingMatch | None:
        stripped = text.strip()

        article_match = ARTICLE_HEADING_RE.match(stripped)
        if article_match:
            return HeadingMatch(
                number=article_match.group("number"),
                title=article_match.group("title").strip(),
                level=1,
                numbering_style=NumberingStyle.ARTICLE,
            )

        section_match = SECTION_HEADING_RE.match(stripped)
        if section_match:
            return HeadingMatch(
                number=section_match.group("number"),
                title=section_match.group("title").strip(),
                level=1,
                numbering_style=NumberingStyle.SECTION,
            )

        numbered_match = NUMBERED_HEADING_RE.match(stripped)
        if numbered_match:
            title = numbered_match.group("title").strip()

            if len(title.split()) <= 10:
                return HeadingMatch(
                    number=numbered_match.group("number"),
                    title=title,
                    level=1,
                    numbering_style=NumberingStyle.DECIMAL,
                )

        return None
