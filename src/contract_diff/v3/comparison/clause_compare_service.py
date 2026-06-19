from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import BinaryIO

from contract_diff.v3.alignment import align_clauses_v3
from contract_diff.v3.comparison.word_diff import diff_clause_words
from contract_diff.v3.extraction import extract_document_text_v3
from contract_diff.v3.extraction.clause_extractor import extract_clauses_v3
from contract_diff.v3.models import (
    V3ClauseAlignment,
    V3ClauseCompareResponse,
    V3ClauseDiff,
    V3CompareSummary,
    V3DebugInfo,
    V3ExtractedClause,
)

PdfInput = bytes | BinaryIO


def compare_clauses_v3(
    original_file: PdfInput,
    revised_file: PdfInput,
    *,
    original_filename: str | None = None,
    revised_filename: str | None = None,
    debug: bool = False,
) -> V3ClauseCompareResponse:
    """Compare two PDFs and return a clause-level v3 JSON response."""

    original_document = extract_document_text_v3(
        original_file,
        filename=original_filename,
    )
    revised_document = extract_document_text_v3(
        revised_file,
        filename=revised_filename,
    )
    original_clauses = extract_clauses_v3(original_document)
    revised_clauses = extract_clauses_v3(revised_document)
    alignments = align_clauses_v3(original_clauses, revised_clauses)

    clause_diffs = [_clause_diff_from_alignment(alignment) for alignment in alignments]
    summary = _build_summary(clause_diffs)

    return V3ClauseCompareResponse(
        document_title=revised_document.title or original_document.title,
        summary=summary,
        clauses=clause_diffs,
        debug=(
            _build_debug_info(
                original_clauses,
                revised_clauses,
                alignments,
                clause_diffs,
            )
            if debug
            else None
        ),
    )


def _clause_diff_from_alignment(alignment: V3ClauseAlignment) -> V3ClauseDiff:
    original_clause = alignment.original_clause
    revised_clause = alignment.revised_clause
    base_clause = revised_clause or original_clause

    if base_clause is None:
        raise ValueError("Alignment must contain an original or revised clause.")

    return V3ClauseDiff(
        id=base_clause.id,
        number=base_clause.number,
        heading=base_clause.heading,
        status=alignment.status,
        original_text=original_clause.text if original_clause is not None else None,
        revised_text=revised_clause.text if revised_clause is not None else None,
        diff_tokens=diff_clause_words(
            original_clause.text if original_clause is not None else None,
            revised_clause.text if revised_clause is not None else None,
        ),
        page_number_original=(
            original_clause.page_number if original_clause is not None else None
        ),
        page_number_revised=(
            revised_clause.page_number if revised_clause is not None else None
        ),
        order_index=alignment.order_index,
    )


def _build_summary(clauses: list[V3ClauseDiff]) -> V3CompareSummary:
    counts = Counter(clause.status for clause in clauses)
    modified = counts.get("modified", 0)
    added = counts.get("added", 0)
    deleted = counts.get("deleted", 0)
    unchanged = counts.get("unchanged", 0)

    return V3CompareSummary(
        total_clauses=len(clauses),
        unchanged_clauses=unchanged,
        changed_clauses=modified + added + deleted,
        added_clauses=added,
        deleted_clauses=deleted,
        modified_clauses=modified,
    )


def _build_debug_info(
    original_clauses: Sequence[V3ExtractedClause],
    revised_clauses: Sequence[V3ExtractedClause],
    alignments: Sequence[V3ClauseAlignment],
    clause_diffs: list[V3ClauseDiff],
) -> V3DebugInfo:
    typed_alignments = list(alignments)
    return V3DebugInfo(
        original_clause_count=len(original_clauses),
        revised_clause_count=len(revised_clauses),
        aligned_clause_count=len(typed_alignments),
        added_clause_ids=[
            clause.id for clause in clause_diffs if clause.status == "added"
        ],
        deleted_clause_ids=[
            clause.id for clause in clause_diffs if clause.status == "deleted"
        ],
        modified_clause_ids=[
            clause.id for clause in clause_diffs if clause.status == "modified"
        ],
        low_confidence_alignments=[
            anchor.id
            for alignment in typed_alignments
            for anchor in [alignment.revised_clause or alignment.original_clause]
            if alignment.confidence < 0.75 and anchor is not None
        ],
        suspicious_large_diffs=[
            clause.id
            for clause in clause_diffs
            if sum(token.type != "equal" for token in clause.diff_tokens) >= 6
            or sum(
                len(token.text.split())
                for token in clause.diff_tokens
                if token.type != "equal"
            )
            > 80
        ],
    )
