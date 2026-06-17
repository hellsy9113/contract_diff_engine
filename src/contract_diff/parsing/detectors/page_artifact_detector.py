import re


class PageArtifactDetector:
    """
    Detects visible page artifacts that should not become legal structure.
    """

    _PAGE_NUMBER_RE = re.compile(r"^Page\s+\d+\s+of\s+\d+$", re.IGNORECASE)
    _SIMPLE_ARTIFACTS = frozenset({"confidential", "draft"})

    @classmethod
    def is_artifact(cls, text: str) -> bool:
        stripped = text.strip()

        if not stripped:
            return True

        if cls._PAGE_NUMBER_RE.match(stripped):
            return True

        return stripped.lower() in cls._SIMPLE_ARTIFACTS
