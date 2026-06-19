from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from contract_diff.comparison.annotation_context import build_annotation_context
from contract_diff.comparison.structured_changes import Change, ChangeType, Location
from contract_diff.extraction.structured.models import (
    BoundingBox,
    DocumentWordStream,
    WordToken,
)

WordDiffType = Literal["equal", "insert", "delete", "replace"]

_BLOCK_ID_RE = re.compile(r"page-\d+-block-(\d+)")
_UNIT_WORDS = frozenset(
    {
        "day",
        "days",
        "month",
        "months",
        "year",
        "years",
        "percent",
        "percentage",
        "dollar",
        "dollars",
        "usd",
        "eur",
        "gbp",
    }
)


class WordDiffOp(BaseModel):
    """One document-level word diff operation."""

    model_config = ConfigDict(frozen=True)

    id: str
    type: WordDiffType
    original_start: int
    original_end: int
    revised_start: int
    revised_end: int
    original_tokens: list[WordToken]
    revised_tokens: list[WordToken]


def diff_word_streams(
    original_stream: DocumentWordStream,
    revised_stream: DocumentWordStream,
) -> list[WordDiffOp]:
    """Compare full-document word streams without page-by-page alignment."""

    original_keys = [token.normalized for token in original_stream.tokens]
    revised_keys = [token.normalized for token in revised_stream.tokens]
    matcher = SequenceMatcher(None, original_keys, revised_keys, autojunk=False)
    ops: list[WordDiffOp] = []

    for (
        tag,
        original_start,
        original_end,
        revised_start,
        revised_end,
    ) in matcher.get_opcodes():
        ops.append(
            WordDiffOp(
                id=f"WOP-{len(ops) + 1:04d}",
                type=tag,
                original_start=original_start,
                original_end=original_end,
                revised_start=revised_start,
                revised_end=revised_end,
                original_tokens=original_stream.slice_tokens(
                    original_start,
                    original_end,
                ),
                revised_tokens=revised_stream.slice_tokens(
                    revised_start,
                    revised_end,
                ),
            )
        )

    return ops


def build_changes_from_word_diff(
    original_stream: DocumentWordStream,
    revised_stream: DocumentWordStream,
) -> list[Change]:
    """Convert document-level word diff ops into renderer-ready changes."""

    changes: list[Change] = []

    for op in diff_word_streams(original_stream, revised_stream):
        if op.type == "equal":
            continue

        change_type = _change_type_for_op(op)
        original_location = _location_for_tokens(op.original_tokens)
        revised_location, anchor_metadata = _revised_location_for_op(
            op,
            revised_stream,
            original_location,
        )
        annotation_context = build_annotation_context(
            op,
            original_stream,
            revised_stream,
        )
        changes.append(
            Change(
                change_id=f"CHG-{len(changes) + 1:04d}",
                change_type=change_type,
                original_text=_tokens_text(op.original_tokens) or None,
                revised_text=_tokens_text(op.revised_tokens) or None,
                original_location=original_location,
                revised_location=revised_location,
                changed_fragments=_changed_fragments(op, revised_stream),
                confidence=_confidence_for_op(op),
                section_path=_section_path_for_op(op),
                metadata={
                    "comparison_strategy": "document_word_diff",
                    "word_diff_operation_id": op.id,
                    "word_diff_operation": op.type,
                    "original_start": op.original_start,
                    "original_end": op.original_end,
                    "revised_start": op.revised_start,
                    "revised_end": op.revised_end,
                    "original_token_ids": [token.id for token in op.original_tokens],
                    "revised_token_ids": [token.id for token in op.revised_tokens],
                    "original_tokens": [
                        token.model_dump() for token in op.original_tokens
                    ],
                    "revised_tokens": [
                        token.model_dump() for token in op.revised_tokens
                    ],
                    "annotation_context": annotation_context.model_dump(),
                    **anchor_metadata,
                },
            )
        )

    return changes


def _change_type_for_op(op: WordDiffOp) -> ChangeType:
    if op.type == "insert":
        return "added"

    if op.type == "delete":
        return "deleted"

    return "modified"


def _tokens_text(tokens: list[WordToken]) -> str:
    return " ".join(token.text for token in tokens).strip()


def _location_for_tokens(tokens: list[WordToken]) -> Location | None:
    if not tokens:
        return None

    page_number = tokens[0].page_number
    page_tokens = [token for token in tokens if token.page_number == page_number]

    return Location(
        page_index=page_number - 1,
        block_index=_block_index(page_tokens[0]),
        bbox=_merge_token_bboxes(page_tokens),
        section_path=_section_path_for_tokens(page_tokens),
    )


def _revised_location_for_op(
    op: WordDiffOp,
    revised_stream: DocumentWordStream,
    original_location: Location | None,
) -> tuple[Location | None, dict[str, Any]]:
    if op.revised_tokens:
        return _location_for_tokens(op.revised_tokens), {
            "revised_location_source": "changed_revised_tokens"
        }

    if op.type == "delete":
        return _delete_anchor_location(
            op,
            revised_stream,
            original_location,
        )

    anchor = _nearest_revised_anchor(op, revised_stream)

    if anchor is None:
        return None, {"revised_location_source": "missing"}

    return _location_for_tokens([anchor]), {
        "revised_location_source": "nearest_revised_token",
        "revised_anchor_token_id": anchor.id,
    }


def _delete_anchor_location(
    op: WordDiffOp,
    revised_stream: DocumentWordStream,
    original_location: Location | None,
) -> tuple[Location | None, dict[str, Any]]:
    after_anchor = _token_at(revised_stream, op.revised_start)

    if after_anchor is not None:
        return _location_for_tokens([after_anchor]), {
            "revised_location_source": "delete_anchor",
            "delete_anchor_strategy": "nearest_surviving_revised_token_after",
            "delete_anchor_token_id": after_anchor.id,
        }

    before_anchor = _token_at(revised_stream, op.revised_start - 1)

    if before_anchor is not None:
        return _location_for_tokens([before_anchor]), {
            "revised_location_source": "delete_anchor",
            "delete_anchor_strategy": "nearest_surviving_revised_token_before",
            "delete_anchor_token_id": before_anchor.id,
        }

    if original_location is not None:
        return original_location, {
            "revised_location_source": "delete_anchor",
            "delete_anchor_strategy": "original_location_fallback",
            "delete_anchor_token_id": None,
        }

    return None, {
        "revised_location_source": "missing",
        "delete_anchor_strategy": "missing",
        "delete_anchor_token_id": None,
    }


def _nearest_revised_anchor(
    op: WordDiffOp,
    revised_stream: DocumentWordStream,
) -> WordToken | None:
    surviving_indexes = frozenset(token.token_index for token in revised_stream.tokens)
    return revised_stream.find_nearest_surviving_anchor(
        op.revised_start,
        surviving_indexes,
    )


def _merge_token_bboxes(tokens: list[WordToken]) -> BoundingBox:
    return BoundingBox(
        x0=min(token.bbox[0] for token in tokens),
        y0=min(token.bbox[1] for token in tokens),
        x1=max(token.bbox[2] for token in tokens),
        y1=max(token.bbox[3] for token in tokens),
    )


def _block_index(token: WordToken) -> int | None:
    if token.block_id is None:
        return None

    match = _BLOCK_ID_RE.fullmatch(token.block_id)

    if match is None:
        return None

    return int(match.group(1))


def _changed_fragments(
    op: WordDiffOp,
    revised_stream: DocumentWordStream,
) -> list[str]:
    if op.type == "delete":
        return []

    fragment = _expanded_revised_fragment(op, revised_stream)

    return [fragment] if fragment else []


def _expanded_revised_fragment(
    op: WordDiffOp,
    revised_stream: DocumentWordStream,
) -> str:
    if not op.revised_tokens:
        return ""

    tokens = op.revised_tokens

    if len(tokens) == 1 and _contains_digit(tokens[0].text):
        next_token = _token_at(revised_stream, op.revised_end)
        previous_token = _token_at(revised_stream, op.revised_start - 1)

        if next_token is not None and _unit_key(next_token) in _UNIT_WORDS:
            tokens = [*tokens, next_token]
        elif previous_token is not None and _unit_key(previous_token) in _UNIT_WORDS:
            tokens = [previous_token, *tokens]

    return _tokens_text(tokens).strip(".,;:!? ")


def _token_at(
    stream: DocumentWordStream,
    index: int,
) -> WordToken | None:
    if index < 0 or index >= len(stream.tokens):
        return None

    return stream.tokens[index]


def _contains_digit(text: str) -> bool:
    return any(character.isdigit() for character in text)


def _unit_key(token: WordToken) -> str:
    return token.normalized.strip(".,;:!?")


def _confidence_for_op(op: WordDiffOp) -> float:
    if op.type in {"insert", "delete"}:
        return 1.0

    original_text = _tokens_text(op.original_tokens)
    revised_text = _tokens_text(op.revised_tokens)

    if not original_text or not revised_text:
        return 0.9

    similarity = SequenceMatcher(
        None,
        original_text.casefold(),
        revised_text.casefold(),
    ).ratio()
    return round(similarity, 4)


def _section_path_for_op(op: WordDiffOp) -> list[str]:
    if op.revised_tokens:
        return _section_path_for_tokens(op.revised_tokens)

    return _section_path_for_tokens(op.original_tokens)


def _section_path_for_tokens(tokens: list[WordToken]) -> list[str]:
    for token in tokens:
        if token.section_heading:
            return [token.section_heading]

    return []
