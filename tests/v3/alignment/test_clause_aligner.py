from contract_diff.v3.alignment.clause_aligner import align_clauses_v3
from contract_diff.v3.models import V3ExtractedClause


def test_same_number_same_text_is_unchanged() -> None:
    original = [
        _clause("clause-1-1", "1.1", "PAYMENT", "1.1 Pay within 30 days.", 0)
    ]
    revised = [
        _clause("clause-1-1", "1.1", "PAYMENT", "1.1 Pay within 30 days.", 0)
    ]

    alignments = align_clauses_v3(original, revised)

    assert len(alignments) == 1
    assert alignments[0].status == "unchanged"
    assert alignments[0].confidence == 1.0


def test_same_number_changed_text_is_modified() -> None:
    original = [
        _clause("clause-4-2", "4.2", "PAYMENT", "4.2 Pay within 30 days.", 0)
    ]
    revised = [
        _clause("clause-4-2", "4.2", "PAYMENT", "4.2 Pay within 15 days.", 0)
    ]

    alignments = align_clauses_v3(original, revised)

    assert len(alignments) == 1
    assert alignments[0].status == "modified"
    assert alignments[0].confidence >= 0.85


def test_clause_only_in_revised_is_added() -> None:
    alignments = align_clauses_v3(
        [],
        [_clause("clause-8-2", "8.2", "CONFIDENTIALITY", "8.2 Return materials.", 0)],
    )

    assert len(alignments) == 1
    assert alignments[0].status == "added"
    assert alignments[0].original_clause is None


def test_clause_only_in_original_is_deleted() -> None:
    alignments = align_clauses_v3(
        [_clause("clause-10-2", "10.2", "LIABILITY", "10.2 No indirect damages.", 0)],
        [],
    )

    assert len(alignments) == 1
    assert alignments[0].status == "deleted"
    assert alignments[0].revised_clause is None


def test_moved_clause_is_aligned_by_similarity_not_page_order() -> None:
    original = [
        _clause(
            "clause-1-1",
            "1.1",
            "PAYMENT",
            "1.1 Pay within 30 days.",
            0,
            page_number=1,
        ),
        _clause(
            "clause-2-1",
            "2.1",
            "TERM",
            "2.1 This agreement lasts one year.",
            1,
            page_number=1,
        ),
    ]
    revised = [
        _clause(
            "clause-2-1",
            "2.1",
            "TERM",
            "2.1 This agreement lasts one year.",
            0,
            page_number=2,
        ),
        _clause(
            "clause-1-1",
            "1.1",
            "PAYMENT",
            "1.1 Pay within 30 days.",
            1,
            page_number=2,
        ),
    ]

    alignments = align_clauses_v3(original, revised)

    assert [alignment.status for alignment in alignments] == [
        "unchanged",
        "unchanged",
    ]
    assert [
        alignment.revised_clause.number
        for alignment in alignments
        if alignment.revised_clause
    ] == ["2.1", "1.1"]


def test_number_changed_but_text_similar_aligns_fuzzily() -> None:
    original = [
        _clause(
            "clause-7-1", "7.1", "TERM", "The term of this agreement is one year.", 0
        )
    ]
    revised = [
        _clause(
            "clause-8-1", "8.1", "TERM", "The term of this agreement is one year.", 0
        )
    ]

    alignments = align_clauses_v3(original, revised)

    assert len(alignments) == 1
    assert alignments[0].status == "unchanged"
    assert alignments[0].confidence >= 0.72


def test_different_clauses_are_not_falsely_aligned() -> None:
    original = [
        _clause("clause-1-1", "1.1", "PAYMENT", "Pay within 30 days.", 0)
    ]
    revised = [
        _clause(
            "clause-9-1",
            "9.1",
            "CONFIDENTIALITY",
            "Return all confidential information.",
            0,
        )
    ]

    alignments = align_clauses_v3(original, revised)

    assert len(alignments) == 2
    assert {alignment.status for alignment in alignments} == {"added", "deleted"}


def _clause(
    clause_id: str,
    number: str | None,
    heading: str | None,
    text: str,
    order_index: int,
    *,
    page_number: int = 1,
) -> V3ExtractedClause:
    return V3ExtractedClause(
        id=clause_id,
        number=number,
        heading=heading,
        text=text,
        page_number=page_number,
        order_index=order_index,
    )
