from contract_diff.normalization.utils.text_normalizer import TextNormalizer


def test_normalize_collapses_whitespace_and_line_breaks() -> None:
    text = "1.   Payment      Terms\nThe Buyer shall pay\r\nwithin 30 days."

    assert (
        TextNormalizer.normalize(text)
        == "1. Payment Terms The Buyer shall pay within 30 days."
    )


def test_normalize_unicode_characters() -> None:
    text = "Buyer\u00a0shall pay “30 days” — no later."

    assert TextNormalizer.normalize(text) == 'Buyer shall pay "30 days" - no later.'
