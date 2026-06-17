from __future__ import annotations

from contract_diff.alignment.scoring.text_similarity import TextSimilarity


class HeadingSimilarity:
    """
    Similarity helpers for section and clause headings.
    """

    @classmethod
    def score(cls, left: str | None, right: str | None) -> float:
        if left is None and right is None:
            return 0.0

        if left is None or right is None:
            return 0.0

        return TextSimilarity.score(left, right)

    @classmethod
    def average_best_match(
        cls,
        left_headings: tuple[str, ...],
        right_headings: tuple[str, ...],
    ) -> float:
        if not left_headings and not right_headings:
            return 100.0

        if not left_headings or not right_headings:
            return 0.0

        left_score = cls._average_direction(left_headings, right_headings)
        right_score = cls._average_direction(right_headings, left_headings)

        return round((left_score + right_score) / 2, 2)

    @classmethod
    def _average_direction(
        cls,
        source: tuple[str, ...],
        candidates: tuple[str, ...],
    ) -> float:
        scores = [
            max(TextSimilarity.score(item, candidate) for candidate in candidates)
            for item in source
        ]

        return sum(scores) / len(scores)
