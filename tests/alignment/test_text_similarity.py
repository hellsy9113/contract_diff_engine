from contract_diff.alignment.scoring.text_similarity import TextSimilarity


def test_exact_text_scores_100() -> None:
    assert (
        TextSimilarity.score("Payment shall be made.", "Payment shall be made.") == 100
    )


def test_similar_text_scores_high() -> None:
    assert (
        TextSimilarity.score(
            "The Buyer shall pay within 30 days.",
            "The Buyer shall pay within 45 days.",
        )
        > 85
    )


def test_unrelated_text_scores_low() -> None:
    assert (
        TextSimilarity.score(
            "The Buyer shall pay within 30 days.",
            "The agreement is governed by California law.",
        )
        < 45
    )
