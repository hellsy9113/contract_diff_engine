from __future__ import annotations

from difflib import SequenceMatcher


class TextSimilarity:
    """
    Deterministic text similarity score from 0 to 100.
    """

    @classmethod
    def score(cls, left: str, right: str) -> float:
        normalized_left = cls._normalize(left)
        normalized_right = cls._normalize(right)

        if not normalized_left and not normalized_right:
            return 100.0

        if not normalized_left or not normalized_right:
            return 0.0

        return round(
            SequenceMatcher(None, normalized_left, normalized_right).ratio() * 100,
            2,
        )

    @classmethod
    def _normalize(cls, text: str) -> str:
        return " ".join(text.casefold().split())
