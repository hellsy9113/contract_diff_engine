from __future__ import annotations

from contract_diff.alignment.scoring.text_similarity import TextSimilarity


class SectionSimilarity:
    """
    Compares section titles for clause alignment scoring.
    """

    @classmethod
    def score(cls, left_title: str | None, right_title: str | None) -> float:
        if left_title is None and right_title is None:
            return 50.0

        if left_title is None or right_title is None:
            return 0.0

        return TextSimilarity.score(left_title, right_title)
