from __future__ import annotations

from contract_diff.comparison.structured_changes import Change
from contract_diff.comparison.word_diff import build_changes_from_word_diff
from contract_diff.debugging.diff_debug import build_diff_debug_payload
from contract_diff.extraction.structured.models import (
    DocumentWordStream,
    PageInfo,
    WordToken,
)
from contract_diff.extraction.structured.word_tokens import normalize_word_token_text


def test_diff_debug_payload_includes_change_details() -> None:
    original = make_stream("The tenant shall pay rent monthly.")
    revised = make_stream("The tenant must pay rent monthly.")
    changes = build_changes_from_word_diff(original, revised)

    payload = build_diff_debug_payload(
        original_file="original.pdf",
        revised_file="revised.pdf",
        original_stream=original,
        revised_stream=revised,
        changes=changes,
    )

    assert payload["original_file"] == "original.pdf"
    assert payload["revised_file"] == "revised.pdf"
    assert payload["total_original_tokens"] == 6
    assert payload["total_revised_tokens"] == 6
    assert payload["total_changes"] == 1
    assert payload["warnings"] == []

    change = payload["changes"][0]
    assert change["id"] == "CHG-0001"
    assert change["type"] == "REPLACE"
    assert change["original_text"] == "shall"
    assert change["revised_text"] == "must"
    assert change["original_token_range"] == [2, 3]
    assert change["revised_token_range"] == [2, 3]
    assert change["page"] == 1
    assert change["section"] == "Payment"
    assert change["highlight_rect_count"] == 1
    assert change["anchor_bbox"] == {
        "x0": 112.0,
        "y0": 72.0,
        "x1": 128.0,
        "y1": 84.0,
    }
    assert change["annotation_context"]["deleted_text"] == "shall"
    assert change["annotation_context"]["inserted_text"] == "must"


def test_diff_debug_payload_adds_safeguard_warnings() -> None:
    original = make_stream(" ".join(f"old{index}" for index in range(81)))
    revised = make_stream("")
    missing_anchor_change = Change(
        change_id="CHG-9999",
        change_type="deleted",
        original_text=None,
        revised_text=None,
        original_location=None,
        revised_location=None,
        changed_fragments=[],
        confidence=1.0,
        section_path=[],
        metadata={},
    )
    changes = [
        *build_changes_from_word_diff(original, revised),
        missing_anchor_change,
    ]

    payload = build_diff_debug_payload(
        original_file=None,
        revised_file=None,
        original_stream=original,
        revised_stream=revised,
        changes=changes,
    )

    warnings = payload["warnings"]

    assert any("giant change detected: CHG-0001" in warning for warning in warnings)
    assert any(
        "more than 30% of document marked changed" in warning for warning in warnings
    )
    assert "missing bbox: CHG-9999" in warnings
    assert "missing anchor: CHG-9999" in warnings
    assert "empty annotation text: CHG-9999" in warnings


def test_diff_debug_payload_warns_when_page_shift_is_suspected() -> None:
    original = make_stream(
        "A central challenge in PQC deployment is computational overhead.",
        page_number=1,
    )
    revised = make_stream(
        "A central challenge in PQC deployment is computational overhead.",
        page_number=2,
    )

    payload = build_diff_debug_payload(
        original_file=None,
        revised_file=None,
        original_stream=original,
        revised_stream=revised,
        changes=[],
    )

    assert "page-shift suspected" in payload["warnings"]


def make_stream(text: str, *, page_number: int = 1) -> DocumentWordStream:
    words = text.split()
    tokens = [
        WordToken(
            id=f"token-{index}",
            text=word,
            normalized=normalize_word_token_text(word),
            page_number=page_number,
            bbox=(72.0 + index * 20.0, 72.0, 88.0 + index * 20.0, 84.0),
            line_id=f"page-{page_number - 1}-block-0-line-0",
            block_id=f"page-{page_number - 1}-block-0",
            paragraph_id=f"page-{page_number - 1}-block-0",
            section_heading="Payment",
            token_index=index,
        )
        for index, word in enumerate(words)
    ]
    return DocumentWordStream(
        tokens=tokens,
        pages=[
            PageInfo(
                page_number=page_number,
                page_index=page_number - 1,
                width=500,
                height=700,
                token_start_index=0 if tokens else None,
                token_end_index=len(tokens) if tokens else None,
            )
        ],
        source_file_name=None,
    )
