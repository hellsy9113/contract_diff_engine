from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from contract_diff.comparison.structured_changes import Change
from contract_diff.comparison.word_diff import build_changes_from_word_diff
from contract_diff.extraction.structured.models import DocumentWordStream
from contract_diff.extraction.structured.pipeline import extract_and_process_pdf
from contract_diff.extraction.structured.word_stream import build_document_word_stream
from contract_diff.extraction.structured.word_tokens import normalize_word_token_text

ORIGINAL_SAMPLE = Path("/home/akarsh/Downloads/updated draft.pdf")
REVISED_SAMPLE = Path("/home/akarsh/Downloads/updated draft-1.pdf")

GROVER_DELETE_SENTENCE = (
    "Apart from Shor’s algorithm, Grover’s algorithm also poses a significant "
    "challenge to modern cryptography."
)
ULTIMATELY_SENTENCE = (
    "Ultimately, this research supports the global transition toward "
    "quantum-resistant security frameworks by identifying key challenges and "
    "proposing foundations for more efficient and practical cryptographic "
    "implementations."
)
FOUNDATIONAL_SENTENCE = (
    "[1, 2, 3, 4, 5] This foundational vulnerability to public key inflation "
    "has sparked significant research into structural and algorithmic "
    "optimization."
)
PKI_DELETE_TEXT = "Public Key Infrastructure"
PAGE_SHIFT_PHRASE = (
    "A central challenge in PQC deployment is the significant computational "
    "overhead and pronounced imbalance between key and ciphertext sizes"
)


@dataclass(frozen=True)
class RealSampleDiff:
    original_stream: DocumentWordStream
    revised_stream: DocumentWordStream
    changes: list[Change]
    original_text: str
    revised_text: str


@pytest.fixture(scope="module")
def real_sample_diff() -> RealSampleDiff:
    missing_paths = [
        path for path in (ORIGINAL_SAMPLE, REVISED_SAMPLE) if not path.exists()
    ]

    if missing_paths:
        pytest.skip(
            "Real sample PDFs are not available: "
            + ", ".join(str(path) for path in missing_paths)
        )

    original_document = extract_and_process_pdf(ORIGINAL_SAMPLE.read_bytes())
    revised_document = extract_and_process_pdf(REVISED_SAMPLE.read_bytes())
    original_stream = build_document_word_stream(original_document)
    revised_stream = build_document_word_stream(revised_document)

    return RealSampleDiff(
        original_stream=original_stream,
        revised_stream=revised_stream,
        changes=build_changes_from_word_diff(original_stream, revised_stream),
        original_text=_stream_text(original_stream),
        revised_text=_stream_text(revised_stream),
    )


def test_real_sample_grover_sentence_is_precise_delete(
    real_sample_diff: RealSampleDiff,
) -> None:
    change = _find_change_by_context(
        real_sample_diff.changes,
        "deleted_text",
        GROVER_DELETE_SENTENCE,
    )
    context = _annotation_context(change)

    assert change.change_type == "deleted"
    assert change.original_text == GROVER_DELETE_SENTENCE
    assert change.revised_text is None
    assert context["before_word"] == "[1]."
    assert context["after_word"] == "It"
    assert context["display_markdown"] == (f"[1]. ~~{GROVER_DELETE_SENTENCE}~~ It")
    assert _metadata_token_count(change, "original_tokens") == 14
    assert _metadata_token_count(change, "revised_tokens") == 0
    assert not _has_modified_change_containing(
        real_sample_diff.changes,
        GROVER_DELETE_SENTENCE,
    )


def test_real_sample_introduction_sentence_change_stays_word_precise(
    real_sample_diff: RealSampleDiff,
) -> None:
    original_has_sentence = ULTIMATELY_SENTENCE in real_sample_diff.original_text
    revised_has_sentence = ULTIMATELY_SENTENCE in real_sample_diff.revised_text

    assert original_has_sentence != revised_has_sentence

    if revised_has_sentence:
        change = _find_change_by_context(
            real_sample_diff.changes,
            "inserted_text",
            ULTIMATELY_SENTENCE,
        )
        assert change.change_type == "added"
        assert _metadata_token_count(change, "revised_tokens") <= 30
    else:
        change = _find_change_by_context(
            real_sample_diff.changes,
            "deleted_text",
            ULTIMATELY_SENTENCE,
        )
        assert change.change_type in {"deleted", "modified"}
        assert _metadata_token_count(change, "original_tokens") <= 30

    context = _annotation_context(change)
    assert context["before_word"]
    assert context["after_word"]
    assert ULTIMATELY_SENTENCE in _context_change_text(context)


def test_real_sample_code_based_sentence_change_has_compact_metadata(
    real_sample_diff: RealSampleDiff,
) -> None:
    original_has_sentence = FOUNDATIONAL_SENTENCE in real_sample_diff.original_text
    revised_has_sentence = FOUNDATIONAL_SENTENCE in real_sample_diff.revised_text

    assert original_has_sentence != revised_has_sentence

    context_key = "inserted_text" if revised_has_sentence else "deleted_text"
    change = _find_change_by_context(
        real_sample_diff.changes,
        context_key,
        FOUNDATIONAL_SENTENCE,
    )
    context = _annotation_context(change)

    assert context["before_word"]
    assert context["after_word"]
    assert FOUNDATIONAL_SENTENCE in _context_change_text(context)
    assert (
        max(
            _metadata_token_count(change, "original_tokens"),
            _metadata_token_count(change, "revised_tokens"),
        )
        <= 35
    )


def test_real_sample_pki_name_is_delete_with_revised_anchor(
    real_sample_diff: RealSampleDiff,
) -> None:
    change = _find_change_by_context(
        real_sample_diff.changes,
        "deleted_text",
        PKI_DELETE_TEXT,
    )
    context = _annotation_context(change)

    assert change.change_type == "deleted"
    assert change.original_text == PKI_DELETE_TEXT
    assert change.revised_text is None
    assert context["before_word"] == "[28]."
    assert context["after_word"] == "(PKI),"
    assert context["display_markdown"] == "[28]. ~~Public Key Infrastructure~~ (PKI),"
    assert change.metadata["delete_anchor_strategy"] == (
        "nearest_surviving_revised_token_after"
    )
    assert change.changed_fragments == []
    assert _metadata_token_count(change, "revised_tokens") == 0


def test_real_sample_page_shifted_text_is_not_marked_changed(
    real_sample_diff: RealSampleDiff,
) -> None:
    original_range = _find_phrase_range(
        real_sample_diff.original_stream,
        PAGE_SHIFT_PHRASE,
    )
    revised_range = _find_phrase_range(
        real_sample_diff.revised_stream,
        PAGE_SHIFT_PHRASE,
    )

    assert original_range is not None
    assert revised_range is not None

    original_page = real_sample_diff.original_stream.tokens[original_range[0]]
    revised_page = real_sample_diff.revised_stream.tokens[revised_range[0]]

    assert original_page.page_number != revised_page.page_number

    for change in real_sample_diff.changes:
        assert PAGE_SHIFT_PHRASE not in _change_blob(change)


def _stream_text(stream: DocumentWordStream) -> str:
    return stream.slice_text(0, len(stream.tokens))


def _find_change_by_context(
    changes: list[Change],
    context_key: str,
    expected_text: str,
) -> Change:
    for change in changes:
        context = change.metadata.get("annotation_context")

        if not isinstance(context, dict):
            continue

        value = context.get(context_key)

        if isinstance(value, str) and expected_text in value:
            return change

    raise AssertionError(f"Could not find change with {context_key}: {expected_text}")


def _annotation_context(change: Change) -> dict[str, Any]:
    context = change.metadata.get("annotation_context")
    assert isinstance(context, dict)
    return context


def _metadata_token_count(change: Change, key: str) -> int:
    tokens = change.metadata.get(key)
    assert isinstance(tokens, list)
    return len(tokens)


def _has_modified_change_containing(
    changes: list[Change],
    expected_text: str,
) -> bool:
    return any(
        change.change_type == "modified" and expected_text in _change_blob(change)
        for change in changes
    )


def _change_blob(change: Change) -> str:
    context = change.metadata.get("annotation_context")
    context_values = ""

    if isinstance(context, dict):
        context_values = " ".join(
            value for value in context.values() if isinstance(value, str)
        )

    return " ".join(
        [
            change.original_text or "",
            change.revised_text or "",
            " ".join(change.changed_fragments),
            context_values,
        ]
    )


def _context_change_text(context: dict[str, Any]) -> str:
    return " ".join(
        str(context.get(key) or "") for key in ("deleted_text", "inserted_text")
    )


def _find_phrase_range(
    stream: DocumentWordStream,
    phrase: str,
) -> tuple[int, int] | None:
    phrase_tokens = [normalize_word_token_text(token) for token in phrase.split()]
    stream_tokens = [token.normalized for token in stream.tokens]
    phrase_length = len(phrase_tokens)

    for start_index in range(0, len(stream_tokens) - phrase_length + 1):
        end_index = start_index + phrase_length

        if stream_tokens[start_index:end_index] == phrase_tokens:
            return start_index, end_index

    return None
