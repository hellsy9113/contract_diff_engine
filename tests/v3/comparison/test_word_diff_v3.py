from contract_diff.v3.comparison.word_diff import diff_clause_words


def test_single_word_replacement_emits_delete_then_insert() -> None:
    tokens = diff_clause_words(
        "The tenant shall pay rent monthly.",
        "The tenant must pay rent monthly.",
    )

    assert [(token.type, token.text) for token in tokens] == [
        ("equal", "The tenant "),
        ("delete", "shall"),
        ("insert", "must"),
        ("equal", " pay rent monthly."),
    ]


def test_number_replacement_is_precise() -> None:
    tokens = diff_clause_words(
        "4.2 Payment shall be made within 30 days of invoice date.",
        "4.2 Payment shall be made within 15 days of invoice date.",
    )

    assert [(token.type, token.text) for token in tokens] == [
        ("equal", "4.2 Payment shall be made within "),
        ("delete", "30"),
        ("insert", "15"),
        ("equal", " days of invoice date."),
    ]


def test_word_insertion_is_precise() -> None:
    tokens = diff_clause_words(
        "The tenant shall pay rent monthly.",
        "The tenant shall pay rent on time monthly.",
    )

    assert [(token.type, token.text) for token in tokens] == [
        ("equal", "The tenant shall pay rent "),
        ("insert", "on time"),
        ("equal", " monthly."),
    ]


def test_word_deletion_is_precise() -> None:
    tokens = diff_clause_words(
        "The tenant shall pay rent monthly.",
        "The tenant shall pay monthly.",
    )

    assert [(token.type, token.text) for token in tokens] == [
        ("equal", "The tenant shall pay "),
        ("delete", "rent"),
        ("equal", " monthly."),
    ]


def test_full_clause_addition_returns_insert_only() -> None:
    clause_text = (
        "8.2 All confidential materials must be returned or destroyed within 10 "
        "business days of termination."
    )
    tokens = diff_clause_words(
        None,
        clause_text,
    )

    assert [(token.type, token.text) for token in tokens] == [("insert", clause_text)]


def test_full_clause_deletion_returns_delete_only() -> None:
    clause_text = (
        "10.2 Neither party shall be liable for indirect, incidental, or "
        "consequential damages."
    )
    tokens = diff_clause_words(
        clause_text,
        None,
    )

    assert [(token.type, token.text) for token in tokens] == [("delete", clause_text)]


def test_punctuation_change_does_not_destroy_surrounding_text() -> None:
    tokens = diff_clause_words("The effective date.", "The effective date!")

    assert [(token.type, token.text) for token in tokens] == [
        ("equal", "The effective date"),
        ("delete", "."),
        ("insert", "!"),
    ]


def test_long_sentence_with_one_word_change_does_not_become_full_replace() -> None:
    tokens = diff_clause_words(
        (
            "The supplier shall maintain insurance coverage throughout the term "
            "and promptly notify the buyer of any material adverse event."
        ),
        (
            "The supplier shall maintain insurance coverage throughout the term "
            "and promptly notify the buyer of any material adverse breach."
        ),
    )

    changed = [token for token in tokens if token.type != "equal"]

    assert [(token.type, token.text) for token in changed] == [
        ("delete", "event"),
        ("insert", "breach"),
    ]
