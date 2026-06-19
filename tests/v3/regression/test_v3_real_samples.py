from __future__ import annotations

from pathlib import Path

import pytest

from contract_diff.v3.comparison.clause_compare_service import compare_clauses_v3
from contract_diff.v3.models import V3ClauseCompareResponse, V3ClauseDiff

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
PKI_DELETE_TEXT = "Public Key Infrastructure"


@pytest.fixture(scope="module")
def real_sample_response() -> V3ClauseCompareResponse:
    missing = [path for path in (ORIGINAL_SAMPLE, REVISED_SAMPLE) if not path.exists()]

    if missing:
        pytest.skip("Real sample PDFs are not available.")

    return compare_clauses_v3(
        ORIGINAL_SAMPLE.read_bytes(),
        REVISED_SAMPLE.read_bytes(),
        original_filename=ORIGINAL_SAMPLE.name,
        revised_filename=REVISED_SAMPLE.name,
        debug=True,
    )


def test_real_sample_grover_sentence_is_delete_not_full_paragraph(
    real_sample_response: V3ClauseCompareResponse,
) -> None:
    clause = _find_clause_containing(
        real_sample_response,
        GROVER_DELETE_SENTENCE,
        changed_only=True,
    )

    changed_text = _changed_token_text(clause)
    assert (
        "Grover’s algorithm also poses a significant challenge to modern cryptography"
        in changed_text
    )
    assert any(token.type == "delete" for token in clause.diff_tokens)
    assert len(clause.diff_tokens) < 8


def test_real_sample_ultimately_sentence_is_precise_delete(
    real_sample_response: V3ClauseCompareResponse,
) -> None:
    clause = _find_clause_containing(
        real_sample_response,
        ULTIMATELY_SENTENCE,
        changed_only=True,
    )

    assert any(token.type == "delete" for token in clause.diff_tokens)
    assert ULTIMATELY_SENTENCE in _changed_token_text(clause)


def test_real_sample_pki_delete_is_precise(
    real_sample_response: V3ClauseCompareResponse,
) -> None:
    clause = _find_clause_containing(
        real_sample_response,
        PKI_DELETE_TEXT,
        changed_only=True,
    )

    assert any(
        token.type == "delete" and PKI_DELETE_TEXT in token.text
        for token in clause.diff_tokens
    )
    assert any(
        token.type == "equal" and "(PKI)" in token.text for token in clause.diff_tokens
    )


def test_real_sample_keeps_some_clauses_unchanged(
    real_sample_response: V3ClauseCompareResponse,
) -> None:
    unchanged_clauses = [
        clause
        for clause in real_sample_response.clauses
        if clause.status == "unchanged"
    ]

    assert unchanged_clauses
    assert any(clause.number == "2.1" for clause in unchanged_clauses)


def test_real_sample_debug_shows_no_paragraph_sized_suspicious_diff(
    real_sample_response: V3ClauseCompareResponse,
) -> None:
    assert real_sample_response.debug is not None
    assert len(real_sample_response.debug.suspicious_large_diffs) < max(
        5,
        real_sample_response.summary.total_clauses // 2,
    )


def _find_clause_containing(
    response: V3ClauseCompareResponse,
    expected_text: str,
    *,
    changed_only: bool = False,
) -> V3ClauseDiff:
    for clause in response.clauses:
        if changed_only and clause.status == "unchanged":
            continue

        blob = " ".join(token.text for token in clause.diff_tokens)
        full_text = " ".join(
            value
            for value in [clause.original_text, clause.revised_text, blob]
            if value is not None
        )

        if expected_text in full_text:
            return clause

    raise AssertionError(f"Could not find clause containing: {expected_text}")


def _changed_token_text(clause: V3ClauseDiff) -> str:
    return " ".join(token.text for token in clause.diff_tokens if token.type != "equal")
