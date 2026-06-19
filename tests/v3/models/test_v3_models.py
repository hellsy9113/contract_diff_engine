from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from contract_diff.v3.models import (
    V3ClauseAlignment,
    V3ClauseCompareResponse,
    V3ClauseDiff,
    V3CompareSummary,
    V3DiffToken,
    V3ExtractedClause,
)


def test_v3_diff_token_serializes_to_json() -> None:
    token = V3DiffToken(type="insert", text="15")

    assert token.model_dump(mode="json") == {
        "type": "insert",
        "text": "15",
    }


def test_v3_extracted_clause_model_creation() -> None:
    clause = V3ExtractedClause(
        id="clause-4-2",
        number="4.2",
        heading="PAYMENT TERMS",
        text="4.2 Payment shall be made within 30 days.",
        page_number=3,
        order_index=7,
    )

    assert clause.id == "clause-4-2"
    assert clause.number == "4.2"
    assert clause.heading == "PAYMENT TERMS"
    assert clause.page_number == 3
    assert clause.order_index == 7


def test_v3_clause_alignment_serializes_nested_clauses() -> None:
    original = _clause("clause-4-2", "30")
    revised = _clause("clause-4-2", "15")
    alignment = V3ClauseAlignment(
        original_clause=original,
        revised_clause=revised,
        status="modified",
        confidence=0.92,
        order_index=2,
    )
    payload = alignment.model_dump(mode="json")

    assert payload["status"] == "modified"
    assert payload["confidence"] == 0.92
    assert payload["original_clause"]["text"] == original.text
    assert payload["revised_clause"]["text"] == revised.text


def test_v3_clause_diff_serializes_diff_tokens() -> None:
    clause_diff = V3ClauseDiff(
        id="clause-4-2",
        number="4.2",
        heading="PAYMENT TERMS",
        status="modified",
        original_text="4.2 Payment shall be made within 30 days.",
        revised_text="4.2 Payment shall be made within 15 days.",
        diff_tokens=[
            V3DiffToken(type="equal", text="4.2 Payment shall be made within "),
            V3DiffToken(type="delete", text="30"),
            V3DiffToken(type="insert", text="15"),
            V3DiffToken(type="equal", text=" days."),
        ],
        page_number_original=1,
        page_number_revised=1,
        order_index=3,
    )

    assert clause_diff.model_dump(mode="json")["diff_tokens"] == [
        {"type": "equal", "text": "4.2 Payment shall be made within "},
        {"type": "delete", "text": "30"},
        {"type": "insert", "text": "15"},
        {"type": "equal", "text": " days."},
    ]


def test_v3_response_defaults_version_and_serializes() -> None:
    response = V3ClauseCompareResponse(
        document_title="PROFESSIONAL SERVICES AGREEMENT",
        summary=V3CompareSummary(
            total_clauses=1,
            unchanged_clauses=0,
            changed_clauses=1,
            added_clauses=0,
            deleted_clauses=0,
            modified_clauses=1,
        ),
        clauses=[
            V3ClauseDiff(
                id="clause-4-2",
                number="4.2",
                heading="PAYMENT TERMS",
                status="modified",
                original_text="4.2 Payment shall be made within 30 days.",
                revised_text="4.2 Payment shall be made within 15 days.",
                diff_tokens=[
                    V3DiffToken(type="delete", text="30"),
                    V3DiffToken(type="insert", text="15"),
                ],
                page_number_original=1,
                page_number_revised=1,
                order_index=0,
            )
        ],
    )
    payload = response.model_dump(mode="json")

    assert payload["version"] == "v3"
    assert payload["document_title"] == "PROFESSIONAL SERVICES AGREEMENT"
    assert payload["summary"]["changed_clauses"] == 1
    assert payload["clauses"][0]["status"] == "modified"
    assert json.loads(response.model_dump_json())["version"] == "v3"


def test_v3_models_validate_literal_values() -> None:
    with pytest.raises(ValidationError):
        V3DiffToken(type="replace", text="invalid")  # type: ignore[arg-type]


def test_v3_alignment_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        V3ClauseAlignment(
            original_clause=None,
            revised_clause=None,
            status="added",
            confidence=1.5,
            order_index=0,
        )


def _clause(clause_id: str, days: str) -> V3ExtractedClause:
    return V3ExtractedClause(
        id=clause_id,
        number="4.2",
        heading="PAYMENT TERMS",
        text=f"4.2 Payment shall be made within {days} days.",
        page_number=1,
        order_index=0,
    )
