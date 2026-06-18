from __future__ import annotations

import re
from difflib import SequenceMatcher

from contract_diff.comparison.enums.fragment_operation import FragmentOperation
from contract_diff.comparison.models.text_fragment import TextFragment
from contract_diff.comparison.utils.text_diff_helpers import normalize_for_alignment


class TextDiffService:
    """
    Deterministic word-level text comparison.
    """

    _TOKEN_RE = re.compile(r"\w+|[^\w\s]")
    _NO_SPACE_BEFORE = frozenset({".", ",", ";", ":", "!", "?", ")", "]", "}"})
    _NO_SPACE_AFTER = frozenset({"(", "[", "{"})

    def equivalent(self, original_text: str, revised_text: str) -> bool:
        return (
            normalize_for_alignment(original_text)
            == normalize_for_alignment(revised_text)
        )

    def normalize_for_comparison(self, text: str) -> str:
        return " ".join(text.split()).strip()

    def diff(self, original_text: str, revised_text: str) -> tuple[TextFragment, ...]:
        original_words = self._words(original_text)
        revised_words = self._words(revised_text)
        matcher = SequenceMatcher(None, original_words, revised_words)
        fragments: list[TextFragment] = []

        for (
            tag,
            original_start,
            original_end,
            revised_start,
            revised_end,
        ) in matcher.get_opcodes():
            if tag == "equal":
                fragments.append(
                    self._fragment(
                        operation=FragmentOperation.EQUAL,
                        sequence_index=len(fragments) + 1,
                        text=self._join(original_words[original_start:original_end]),
                    )
                )
                continue

            if tag == "delete":
                fragments.append(
                    self._fragment(
                        operation=FragmentOperation.DELETED,
                        sequence_index=len(fragments) + 1,
                        original_text=self._join(
                            original_words[original_start:original_end]
                        ),
                    )
                )
                continue

            if tag == "insert":
                fragments.append(
                    self._fragment(
                        operation=FragmentOperation.INSERTED,
                        sequence_index=len(fragments) + 1,
                        revised_text=self._join(
                            revised_words[revised_start:revised_end]
                        ),
                    )
                )
                continue

            deleted_text = self._join(original_words[original_start:original_end])
            inserted_text = self._join(revised_words[revised_start:revised_end])

            if deleted_text:
                fragments.append(
                    self._fragment(
                        operation=FragmentOperation.DELETED,
                        sequence_index=len(fragments) + 1,
                        original_text=deleted_text,
                    )
                )

            if inserted_text:
                fragments.append(
                    self._fragment(
                        operation=FragmentOperation.INSERTED,
                        sequence_index=len(fragments) + 1,
                        revised_text=inserted_text,
                    )
                )

        return tuple(fragment for fragment in fragments if self._has_text(fragment))

    def _words(self, text: str) -> tuple[str, ...]:
        return tuple(self._TOKEN_RE.findall(self.normalize_for_comparison(text)))

    def _join(self, words: tuple[str, ...]) -> str:
        text = ""

        for word in words:
            if not text:
                text = word
                continue

            if word in self._NO_SPACE_BEFORE or text[-1] in self._NO_SPACE_AFTER:
                text += word
            else:
                text += f" {word}"

        return text

    def _fragment(
        self,
        operation: FragmentOperation,
        sequence_index: int,
        text: str | None = None,
        original_text: str | None = None,
        revised_text: str | None = None,
    ) -> TextFragment:
        return TextFragment(
            operation=operation,
            sequence_index=sequence_index,
            text=text,
            original_text=original_text,
            revised_text=revised_text,
        )

    def _has_text(self, fragment: TextFragment) -> bool:
        return any((fragment.text, fragment.original_text, fragment.revised_text))
