from __future__ import annotations

from difflib import SequenceMatcher

from contract_diff.extraction.structured.word_tokens import normalize_word_token_text
from contract_diff.v3.models import (
    V3ClauseAlignment,
    V3ClauseStatus,
    V3ExtractedClause,
)

_FUZZY_ALIGNMENT_THRESHOLD = 0.72


def align_clauses_v3(
    original_clauses: list[V3ExtractedClause],
    revised_clauses: list[V3ExtractedClause],
) -> list[V3ClauseAlignment]:
    """Align original and revised clauses by number first, then text similarity."""

    original_by_number = {
        clause.number: clause
        for clause in original_clauses
        if clause.number is not None
    }
    matched_original_ids: set[str] = set()
    alignments: list[V3ClauseAlignment] = []

    for revised_clause in revised_clauses:
        original_clause = None
        status: V3ClauseStatus = "added"
        confidence = 0.0

        if revised_clause.number is not None:
            original_clause = original_by_number.get(revised_clause.number)

        if original_clause is not None:
            matched_original_ids.add(original_clause.id)
            normalized_original = _normalize_clause_text(original_clause.text)
            normalized_revised = _normalize_clause_text(revised_clause.text)

            if normalized_original == normalized_revised:
                status = "unchanged"
                confidence = 1.0
            else:
                status = "modified"
                confidence = max(
                    0.85,
                    SequenceMatcher(
                        None,
                        normalized_original,
                        normalized_revised,
                        autojunk=False,
                    ).ratio(),
                )
        else:
            fuzzy_match = _best_fuzzy_match(
                revised_clause,
                original_clauses,
                matched_original_ids,
            )

            if fuzzy_match is not None:
                original_clause, confidence = fuzzy_match
                matched_original_ids.add(original_clause.id)
                status = (
                    "unchanged"
                    if _normalize_clause_text(original_clause.text)
                    == _normalize_clause_text(revised_clause.text)
                    else "modified"
                )

        alignments.append(
            V3ClauseAlignment(
                original_clause=original_clause,
                revised_clause=revised_clause,
                status=status,
                confidence=confidence,
                order_index=revised_clause.order_index,
            )
        )

    deleted_alignments = [
        V3ClauseAlignment(
            original_clause=clause,
            revised_clause=None,
            status="deleted",
            confidence=1.0,
            order_index=clause.order_index,
        )
        for clause in original_clauses
        if clause.id not in matched_original_ids
    ]

    return _merge_deleted_alignments(alignments, deleted_alignments)


def _best_fuzzy_match(
    revised_clause: V3ExtractedClause,
    original_clauses: list[V3ExtractedClause],
    matched_original_ids: set[str],
) -> tuple[V3ExtractedClause, float] | None:
    best_match: V3ExtractedClause | None = None
    best_score = 0.0
    revised_text = _normalize_clause_text(revised_clause.text)

    for original_clause in original_clauses:
        if original_clause.id in matched_original_ids:
            continue

        score = SequenceMatcher(
            None,
            _normalize_clause_text(original_clause.text),
            revised_text,
            autojunk=False,
        ).ratio()

        if (
            original_clause.number is not None
            and revised_clause.number is not None
            and original_clause.number != revised_clause.number
            and score < 0.92
        ):
            continue

        if (
            original_clause.heading is not None
            and revised_clause.heading is not None
            and normalize_word_token_text(original_clause.heading)
            == normalize_word_token_text(revised_clause.heading)
        ):
            score += 0.05

        if score > best_score:
            best_score = score
            best_match = original_clause

    if best_match is None or best_score < _FUZZY_ALIGNMENT_THRESHOLD:
        return None

    return best_match, min(best_score, 0.99)


def _merge_deleted_alignments(
    alignments: list[V3ClauseAlignment],
    deleted_alignments: list[V3ClauseAlignment],
) -> list[V3ClauseAlignment]:
    if not deleted_alignments:
        return alignments

    merged = list(alignments)

    for deleted in deleted_alignments:
        insert_at = len(merged)

        for index, alignment in enumerate(merged):
            revised_clause = alignment.revised_clause

            if (
                revised_clause is not None
                and revised_clause.order_index > deleted.order_index
            ):
                insert_at = index
                break

        merged.insert(insert_at, deleted)

    for index, alignment in enumerate(merged):
        merged[index] = alignment.model_copy(update={"order_index": index})

    return merged


def _normalize_clause_text(text: str) -> str:
    parts = [normalize_word_token_text(part) for part in text.split()]
    return " ".join(part for part in parts if part)
