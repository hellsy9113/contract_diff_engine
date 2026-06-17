from pydantic import BaseModel, ConfigDict

from contract_diff.parsing.rules.definition_rules import (
    QUOTED_DEFINITION_RE,
    TERM_DEFINITION_RE,
)


class DefinitionMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    term: str
    text: str


class DefinitionDetector:
    """
    Detects common legal definition forms with deterministic regexes.
    """

    @classmethod
    def detect(cls, text: str) -> DefinitionMatch | None:
        stripped = text.strip()

        for pattern in (QUOTED_DEFINITION_RE, TERM_DEFINITION_RE):
            match = pattern.match(stripped)

            if match:
                return DefinitionMatch(
                    term=match.group("term").strip(),
                    text=stripped,
                )

        return None
