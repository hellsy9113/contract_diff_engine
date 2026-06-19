from contract_diff.alignment.scoring.clause_similarity import ClauseSimilarityScorer
from tests.alignment.helpers import make_clause, make_document, make_section


def test_exact_clause_numbers_match_strongly() -> None:
    original = make_document(
        (make_clause("orig-1", "The Buyer shall pay within 30 days.", "3.2"),)
    )
    revised = make_document(
        (make_clause("rev-1", "The Buyer shall pay within 45 days.", "3.2"),)
    )

    score = ClauseSimilarityScorer.score(
        original.clauses[0],
        revised.clauses[0],
        original,
        revised,
        0,
        0,
    )

    assert score.clause_number_score == 100
    assert score.overall >= 80


def test_renumbered_but_similar_text_still_matches() -> None:
    original = make_document(
        (make_clause("orig-1", "The Buyer shall pay within 30 days.", "4.2"),)
    )
    revised = make_document(
        (make_clause("rev-1", "The Buyer shall pay within 30 days.", "5.1"),)
    )

    score = ClauseSimilarityScorer.score(
        original.clauses[0],
        revised.clauses[0],
        original,
        revised,
        0,
        0,
    )

    assert score.text_score == 100
    assert score.overall >= 60


def test_similar_headings_improve_score() -> None:
    original = make_document(
        (
            make_clause(
                "orig-1",
                "Termination may occur for cause.",
                "7.1",
                title="Termination for Cause",
            ),
        ),
        sections=(make_section("section-1", "Termination"),),
    )
    revised = make_document(
        (
            make_clause(
                "rev-1",
                "Termination may occur for cause.",
                "8.1",
                title="Termination",
            ),
        ),
        sections=(make_section("section-1", "Termination"),),
    )

    score = ClauseSimilarityScorer.score(
        original.clauses[0],
        revised.clauses[0],
        original,
        revised,
        0,
        0,
    )

    assert score.heading_score > 60


def test_different_clauses_do_not_match() -> None:
    original = make_document(
        (make_clause("orig-1", "The Buyer shall pay within 30 days.", "1.1"),),
        sections=(make_section("section-1", "Payment"),),
    )
    revised = make_document(
        (make_clause("rev-1", "This agreement is governed by Delaware law.", "9.1"),),
        sections=(make_section("section-1", "Governing Law"),),
    )

    score = ClauseSimilarityScorer.score(
        original.clauses[0],
        revised.clauses[0],
        original,
        revised,
        0,
        0,
    )

    assert score.overall < 60
