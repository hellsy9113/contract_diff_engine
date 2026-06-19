from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from contract_diff.comparison.structured_changes import Change, Location
from contract_diff.extraction.structured.models import (
    BoundingBox,
    DocumentWordStream,
    WordToken,
)
from contract_diff.rendering.utils.token_bboxes import group_changed_token_bboxes

GIANT_CHANGE_TOKEN_LIMIT = 80
CHANGED_DOCUMENT_RATIO_LIMIT = 0.30

_WORD_TOKEN_LIST = TypeAdapter(list[WordToken])


def write_diff_debug_json(
    output_path: Path,
    *,
    original_file: str | None,
    revised_file: str | None,
    original_stream: DocumentWordStream,
    revised_stream: DocumentWordStream,
    changes: list[Change],
) -> None:
    """Write a development-only JSON sidecar for a comparison run."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_diff_debug_payload(
        original_file=original_file,
        revised_file=revised_file,
        original_stream=original_stream,
        revised_stream=revised_stream,
        changes=changes,
    )
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def build_diff_debug_payload(
    *,
    original_file: str | None,
    revised_file: str | None,
    original_stream: DocumentWordStream,
    revised_stream: DocumentWordStream,
    changes: list[Change],
) -> dict[str, Any]:
    warnings: list[str] = []
    debug_changes = [_debug_change(change, warnings) for change in changes]
    warnings.extend(
        _document_level_warnings(
            original_stream=original_stream,
            revised_stream=revised_stream,
            changes=changes,
        )
    )

    return {
        "original_file": original_file,
        "revised_file": revised_file,
        "total_original_tokens": len(original_stream.tokens),
        "total_revised_tokens": len(revised_stream.tokens),
        "total_changes": len(changes),
        "changes": debug_changes,
        "warnings": _unique(warnings),
    }


def _debug_change(
    change: Change,
    warnings: list[str],
) -> dict[str, Any]:
    original_tokens = _word_tokens(change, "original_tokens")
    revised_tokens = _word_tokens(change, "revised_tokens")
    token_count = max(len(original_tokens), len(revised_tokens))
    location = change.revised_location or change.original_location
    context = _annotation_context(change)

    if token_count > GIANT_CHANGE_TOKEN_LIMIT:
        warnings.append(
            f"giant change detected: {change.change_id} contains {token_count} tokens"
        )

    if _bbox_for_location(location) is None:
        warnings.append(f"missing bbox: {change.change_id}")

    if change.change_type == "deleted" and change.revised_location is None:
        warnings.append(f"missing anchor: {change.change_id}")

    if not _annotation_text(change):
        warnings.append(f"empty annotation text: {change.change_id}")

    return {
        "id": change.change_id,
        "type": _debug_change_type(change),
        "original_text": change.original_text,
        "revised_text": change.revised_text,
        "annotation_context": context,
        "original_token_range": _token_range(change, "original"),
        "revised_token_range": _token_range(change, "revised"),
        "page": _page(location),
        "section": _section(change, location),
        "highlight_rect_count": _highlight_rect_count(change, revised_tokens),
        "anchor_bbox": _bbox_for_location(location),
    }


def _document_level_warnings(
    *,
    original_stream: DocumentWordStream,
    revised_stream: DocumentWordStream,
    changes: list[Change],
) -> list[str]:
    warnings: list[str] = []
    total_tokens = len(original_stream.tokens) + len(revised_stream.tokens)
    changed_tokens = sum(
        _metadata_range_length(change, "original")
        + _metadata_range_length(change, "revised")
        for change in changes
    )

    if total_tokens and changed_tokens / total_tokens > CHANGED_DOCUMENT_RATIO_LIMIT:
        warnings.append(
            "more than 30% of document marked changed: "
            f"{changed_tokens}/{total_tokens} tokens"
        )

    if _page_shift_suspected(original_stream, revised_stream):
        warnings.append("page-shift suspected")

    return warnings


def _debug_change_type(change: Change) -> str:
    if change.change_type == "added":
        return "INSERT"

    if change.change_type == "deleted":
        return "DELETE"

    if change.change_type == "modified":
        return "REPLACE"

    return change.change_type.replace("_", " ").upper()


def _annotation_context(change: Change) -> dict[str, Any] | None:
    context = change.metadata.get("annotation_context")
    return context if isinstance(context, dict) else None


def _annotation_text(change: Change) -> str:
    context = _annotation_context(change)
    values: list[str] = []

    if context is not None:
        values.extend(
            value.strip()
            for value in context.values()
            if isinstance(value, str) and value.strip()
        )

    values.extend(
        value.strip()
        for value in (
            change.original_text,
            change.revised_text,
            *change.changed_fragments,
        )
        if isinstance(value, str) and value.strip()
    )
    return " ".join(values).strip()


def _token_range(change: Change, side: str) -> list[int] | None:
    start = change.metadata.get(f"{side}_start")
    end = change.metadata.get(f"{side}_end")

    if isinstance(start, int) and isinstance(end, int):
        return [start, end]

    return None


def _metadata_range_length(change: Change, side: str) -> int:
    token_range = _token_range(change, side)

    if token_range is None:
        return 0

    return max(0, token_range[1] - token_range[0])


def _word_tokens(change: Change, metadata_key: str) -> list[WordToken]:
    raw_tokens = change.metadata.get(metadata_key)

    if not isinstance(raw_tokens, list):
        return []

    try:
        return _WORD_TOKEN_LIST.validate_python(raw_tokens)
    except ValidationError:
        return []


def _highlight_rect_count(change: Change, revised_tokens: list[WordToken]) -> int:
    if change.change_type == "deleted":
        return 0

    if revised_tokens:
        return len(group_changed_token_bboxes(revised_tokens))

    if change.revised_location is not None and change.revised_location.bbox is not None:
        return 1

    return 0


def _page(location: Location | None) -> int | None:
    if location is None:
        return None

    return location.page_index + 1


def _section(change: Change, location: Location | None) -> str | None:
    if change.section_path:
        return " > ".join(change.section_path)

    if location is not None and location.section_path:
        return " > ".join(location.section_path)

    return None


def _bbox_for_location(location: Location | None) -> dict[str, float] | None:
    if location is None or location.bbox is None:
        return None

    return _bbox(location.bbox)


def _bbox(bbox: BoundingBox) -> dict[str, float]:
    return {
        "x0": bbox.x0,
        "y0": bbox.y0,
        "x1": bbox.x1,
        "y1": bbox.y1,
    }


def _page_shift_suspected(
    original_stream: DocumentWordStream,
    revised_stream: DocumentWordStream,
) -> bool:
    window_size = 8

    if (
        len(original_stream.tokens) < window_size
        or len(revised_stream.tokens) < window_size
    ):
        return False

    revised_windows = {
        _window_key(
            revised_stream.tokens[index : index + window_size]
        ): revised_stream.tokens[index].page_number
        for index in range(0, len(revised_stream.tokens) - window_size + 1)
    }

    for index in range(0, len(original_stream.tokens) - window_size + 1):
        key = _window_key(original_stream.tokens[index : index + window_size])
        revised_page = revised_windows.get(key)

        if (
            revised_page is not None
            and revised_page != original_stream.tokens[index].page_number
        ):
            return True

    return False


def _window_key(tokens: list[WordToken]) -> tuple[str, ...]:
    return tuple(token.normalized for token in tokens)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
