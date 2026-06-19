from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TypedDict, cast

from contract_diff.parsing.detectors.clause_number_detector import ClauseNumberDetector
from contract_diff.parsing.detectors.heading_detector import HeadingDetector
from contract_diff.v3.models import V3DocumentText, V3ExtractedClause

_UPPERCASE_HEADING_RE = re.compile(r"^[A-Z][A-Z0-9\s,&/().'-]{2,80}$")


class ClauseCandidate(TypedDict):
    page_number: int
    text: str
    number: str | None
    heading: str | None


def extract_clauses_v3(document: V3DocumentText) -> list[V3ExtractedClause]:
    """Extract numbered clauses or paragraph chunks from v3 page text."""

    candidates = list(_iter_candidates(document))

    if any(candidate["number"] is not None for candidate in candidates):
        return _build_numbered_clauses(candidates)

    return _build_fallback_paragraph_clauses(candidates)


def _iter_candidates(
    document: V3DocumentText,
) -> Iterable[ClauseCandidate]:
    current_heading: str | None = None
    current_heading_number: str | None = None

    for page in document.pages:
        lines = _logical_lines(page.text)

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            heading = HeadingDetector.detect(stripped)
            if heading is not None:
                current_heading = heading.title
                current_heading_number = heading.number
                continue

            if _is_uppercase_heading(stripped):
                current_heading = stripped
                current_heading_number = None
                continue

            clause_match = ClauseNumberDetector.detect(stripped)
            if clause_match is not None:
                yield {
                    "page_number": page.page_number,
                    "text": stripped,
                    "number": clause_match.number,
                    "heading": _resolved_heading(
                        current_heading,
                        current_heading_number,
                        clause_match.number,
                    ),
                }
                continue

            yield {
                "page_number": page.page_number,
                "text": stripped,
                "number": None,
                "heading": current_heading,
            }


def _build_numbered_clauses(
    candidates: list[ClauseCandidate],
) -> list[V3ExtractedClause]:
    clauses: list[V3ExtractedClause] = []
    pending: ClauseCandidate | None = None
    standalone_candidates: list[ClauseCandidate] = []

    for candidate in candidates:
        text = str(candidate["text"]).strip()
        number = candidate["number"]

        if number is not None:
            if standalone_candidates:
                clauses.extend(
                    _build_fallback_paragraph_clauses(
                        standalone_candidates,
                        start_index=len(clauses),
                    )
                )
                standalone_candidates = []

            if pending is not None:
                clauses.append(_clause_from_pending(pending, len(clauses)))
            pending = cast(ClauseCandidate, dict(candidate))
            continue

        if pending is None:
            standalone_candidates.append(candidate)
            continue

        if candidate["heading"] != pending["heading"]:
            clauses.append(_clause_from_pending(pending, len(clauses)))
            pending = None
            standalone_candidates.append(candidate)
            continue

        pending["text"] = f"{pending['text']} {text}".strip()

    if pending is not None:
        clauses.append(_clause_from_pending(pending, len(clauses)))

    if standalone_candidates:
        clauses.extend(
            _build_fallback_paragraph_clauses(
                standalone_candidates,
                start_index=len(clauses),
            )
        )

    if clauses:
        return clauses

    return _build_fallback_paragraph_clauses(candidates)


def _build_fallback_paragraph_clauses(
    candidates: list[ClauseCandidate],
    *,
    start_index: int = 0,
) -> list[V3ExtractedClause]:
    clauses: list[V3ExtractedClause] = []
    grouped: list[ClauseCandidate] = []

    for candidate in candidates:
        text = str(candidate["text"]).strip()

        if not text:
            continue

        if grouped and _can_merge_fallback(grouped[-1], candidate):
            grouped[-1]["text"] = f"{grouped[-1]['text']} {text}".strip()
            continue

        grouped.append(cast(ClauseCandidate, dict(candidate)))

    for index, candidate in enumerate(grouped, start=1):
        clause_index = start_index + index - 1
        clauses.append(
            V3ExtractedClause(
                id=f"clause-{clause_index + 1:04d}",
                number=None,
                heading=_as_optional_str(candidate["heading"]),
                text=str(candidate["text"]).strip(),
                page_number=candidate["page_number"],
                order_index=clause_index,
            )
        )

    return clauses


def _clause_from_pending(
    pending: ClauseCandidate,
    clause_index: int,
) -> V3ExtractedClause:
    number = str(pending["number"])
    return V3ExtractedClause(
        id=_clause_id_from_number(number),
        number=number,
        heading=_as_optional_str(pending["heading"]),
        text=str(pending["text"]).strip(),
        page_number=pending["page_number"],
        order_index=clause_index,
    )


def _clause_id_from_number(number: str) -> str:
    safe_number = re.sub(r"[^0-9A-Za-z]+", "-", number).strip("-").lower()
    return f"clause-{safe_number}" if safe_number else "clause-0000"


def _logical_lines(page_text: str) -> list[str]:
    paragraphs = [chunk for chunk in re.split(r"\n\s*\n+", page_text) if chunk.strip()]
    lines: list[str] = []

    for paragraph in paragraphs:
        raw_lines = [" ".join(line.split()).strip() for line in paragraph.splitlines()]
        lines.extend(_merge_wrapped_lines(raw_lines))

    return lines


def _merge_wrapped_lines(raw_lines: list[str]) -> list[str]:
    merged: list[str] = []

    for line in raw_lines:
        if not line:
            continue

        if not merged or _starts_new_logical_line(line, merged[-1]):
            merged.append(line)
            continue

        merged[-1] = f"{merged[-1]} {line}".strip()

    return merged


def _starts_new_logical_line(line: str, previous: str) -> bool:
    if HeadingDetector.detect(line) is not None:
        return True

    if ClauseNumberDetector.detect(line) is not None:
        return True

    if _is_uppercase_heading(line):
        return True

    return previous.endswith((".", "!", "?", ":"))


def _resolved_heading(
    current_heading: str | None,
    current_heading_number: str | None,
    clause_number: str,
) -> str | None:
    if current_heading is None:
        return None

    if current_heading_number is None:
        return current_heading

    clause_prefix = clause_number.split(".")[0]

    if current_heading_number == clause_prefix:
        return current_heading

    return current_heading


def _is_uppercase_heading(text: str) -> bool:
    if not _UPPERCASE_HEADING_RE.fullmatch(text):
        return False

    alpha_chars = [char for char in text if char.isalpha()]
    return bool(alpha_chars) and all(char.isupper() for char in alpha_chars)


def _can_merge_fallback(
    previous: ClauseCandidate,
    current: ClauseCandidate,
) -> bool:
    previous_heading = _as_optional_str(previous["heading"])
    current_heading = _as_optional_str(current["heading"])
    previous_page = previous["page_number"]
    current_page = current["page_number"]
    previous_text = str(previous["text"])

    if previous_page != current_page:
        return False

    if previous_heading != current_heading:
        return False

    return previous_text[-1] not in ".!?:;"


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None
