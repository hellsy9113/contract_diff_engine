class AnnotationIdService:
    """
    Generates stable sequential annotation identifiers.
    """

    def __init__(self, prefix: str = "ANN") -> None:
        self._prefix = prefix
        self._next_number = 1

    def next_id(self) -> str:
        annotation_id = f"{self._prefix}-{self._next_number}"
        self._next_number += 1
        return annotation_id
