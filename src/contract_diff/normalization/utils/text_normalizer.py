from __future__ import annotations

import re
import unicodedata


class TextNormalizer:
    """
    Safe text normalization that does not alter source references.
    """

    _WHITESPACE_RE = re.compile(r"\s+")
    _UNICODE_TRANSLATION = str.maketrans(
        {
            "\u00a0": " ",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "-",
        }
    )

    @classmethod
    def normalize(cls, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text)
        normalized = normalized.translate(cls._UNICODE_TRANSLATION)
        normalized = cls._WHITESPACE_RE.sub(" ", normalized)

        return normalized.strip()
