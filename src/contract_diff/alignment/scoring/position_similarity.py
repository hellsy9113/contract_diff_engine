from __future__ import annotations


class PositionSimilarity:
    """
    Scores relative clause position from 0 to 100.
    """

    @classmethod
    def score(
        cls,
        left_index: int,
        right_index: int,
        left_count: int,
        right_count: int,
    ) -> float:
        left_position = cls._relative_position(left_index, left_count)
        right_position = cls._relative_position(right_index, right_count)
        distance = abs(left_position - right_position)

        return round(max(0.0, 100.0 - (distance * 100.0)), 2)

    @classmethod
    def _relative_position(cls, index: int, count: int) -> float:
        if count <= 1:
            return 0.0

        return index / (count - 1)
