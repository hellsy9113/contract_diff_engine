from __future__ import annotations

from contract_diff.alignment.scoring.text_similarity import TextSimilarity


class NumberSimilarity:
    """
    Deterministic clause number similarity score from 0 to 100.
    """

    @classmethod
    def score(cls, left: str | None, right: str | None) -> float:
        if left == right and left is not None:
            return 100.0

        if left is None and right is None:
            return 50.0

        if left is None or right is None:
            return 0.0

        if cls._top_level(left) == cls._top_level(right):
            return 60.0

        return round(TextSimilarity.score(left, right) * 0.75, 2)

    @classmethod
    def _top_level(cls, number: str) -> str:
        return number.split(".", maxsplit=1)[0].split("(", maxsplit=1)[0]
