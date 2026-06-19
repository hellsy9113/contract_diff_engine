from __future__ import annotations

import fitz  # type: ignore[import-untyped]
import pytest

from contract_diff.v3.comparison import clause_compare_service
from contract_diff.v3.comparison.clause_compare_service import compare_clauses_v3
from contract_diff.v3.models import V3DocumentText, V3PageText


def test_service_returns_v3_response_with_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = _document(
        "4. PAYMENT TERMS\n\n4.2 Payment shall be made within 30 days of invoice date."
    )
    revised = _document(
        "4. PAYMENT TERMS\n\n4.2 Payment shall be made within 15 days of invoice date."
    )
    _patch_adapter(monkeypatch, [original, revised])

    response = compare_clauses_v3(b"%PDF original", b"%PDF revised")

    assert response.version == "v3"
    assert response.summary.total_clauses == 1
    assert response.summary.modified_clauses == 1
    assert response.summary.changed_clauses == 1
    assert response.debug is None


def test_service_returns_added_deleted_and_unchanged_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = _document(
        "1. GENERAL\n\n1.1 Intro clause.\n\n1.2 Deleted clause.\n\n1.3 Shared clause."
    )
    revised = _document(
        "1. GENERAL\n\n1.1 Intro clause.\n\n1.3 Shared clause.\n\n1.4 Added clause."
    )
    _patch_adapter(monkeypatch, [original, revised])

    response = compare_clauses_v3(b"o", b"r")

    statuses = {clause.number: clause.status for clause in response.clauses}
    assert statuses["1.1"] == "unchanged"
    assert statuses["1.2"] == "deleted"
    assert statuses["1.4"] == "added"

    deleted_clause = next(
        clause for clause in response.clauses if clause.number == "1.2"
    )
    added_clause = next(clause for clause in response.clauses if clause.number == "1.4")
    unchanged_clause = next(
        clause for clause in response.clauses if clause.number == "1.1"
    )

    assert [token.type for token in deleted_clause.diff_tokens] == ["delete"]
    assert [token.type for token in added_clause.diff_tokens] == ["insert"]
    assert all(token.type == "equal" for token in unchanged_clause.diff_tokens)


def test_service_debug_mode_returns_safe_debug_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = _document("1.1 Pay within 30 days.")
    revised = _document("1.1 Pay within 15 days.")
    _patch_adapter(monkeypatch, [original, revised])

    response = compare_clauses_v3(
        b"%PDF original",
        b"%PDF revised",
        debug=True,
        original_filename="original.pdf",
        revised_filename="revised.pdf",
    )

    assert response.debug is not None
    assert response.debug.original_clause_count == 1
    assert response.debug.revised_clause_count == 1
    assert response.debug.modified_clause_ids == ["clause-1-1"]


def test_service_works_end_to_end_with_real_pdf_bytes() -> None:
    original_pdf = _make_pdf(
        "4. PAYMENT TERMS\n\n4.2 Payment shall be made within 30 days of invoice date."
    )
    revised_pdf = _make_pdf(
        "4. PAYMENT TERMS\n\n4.2 Payment shall be made within 15 days of invoice date."
    )

    response = compare_clauses_v3(original_pdf, revised_pdf)

    assert response.summary.total_clauses >= 1
    clause = next(clause for clause in response.clauses if clause.number == "4.2")
    assert clause.status == "modified"
    assert [token.type for token in clause.diff_tokens] == [
        "equal",
        "delete",
        "insert",
        "equal",
    ]


def _patch_adapter(
    monkeypatch: pytest.MonkeyPatch,
    documents: list[V3DocumentText],
) -> None:
    queue = list(documents)

    def fake_extract_document_text_v3(
        _file: object,
        filename: str | None = None,
    ) -> V3DocumentText:
        assert filename is None or filename.endswith(".pdf")
        return queue.pop(0)

    monkeypatch.setattr(
        clause_compare_service,
        "extract_document_text_v3",
        fake_extract_document_text_v3,
    )


def _document(text: str) -> V3DocumentText:
    return V3DocumentText(
        full_text=text,
        pages=[V3PageText(page_number=1, text=text)],
    )


def _make_pdf(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    lines = text.splitlines() or [text]

    for index, line in enumerate(lines):
        page.insert_text((72, 72 + index * 18), line)

    return bytes(document.write())
