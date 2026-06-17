from contract_diff.parsing.detectors.clause_number_detector import (
    ClauseNumberDetector,
)
from contract_diff.parsing.enums.numbering_style import NumberingStyle


def test_detect_numbered_clause() -> None:
    clause_number = ClauseNumberDetector.detect(
        "2.1 The Buyer shall pay within thirty days."
    )

    assert clause_number is not None
    assert clause_number.number == "2.1"
    assert clause_number.body == "The Buyer shall pay within thirty days."
    assert clause_number.numbering_style is NumberingStyle.NESTED_DECIMAL


def test_detect_nested_clause_number() -> None:
    clause_number = ClauseNumberDetector.detect(
        "4.3(a) The Supplier shall indemnify the Buyer."
    )

    assert clause_number is not None
    assert clause_number.number == "4.3(a)"
    assert clause_number.body == "The Supplier shall indemnify the Buyer."


def test_detect_standalone_letter_clause_marker() -> None:
    clause_number = ClauseNumberDetector.detect("(a) The obligations survive.")

    assert clause_number is not None
    assert clause_number.number == "(a)"
    assert clause_number.body == "The obligations survive."
    assert clause_number.numbering_style is NumberingStyle.LETTER


def test_detect_standalone_roman_clause_marker() -> None:
    clause_number = ClauseNumberDetector.detect("(i) The first condition.")

    assert clause_number is not None
    assert clause_number.number == "(i)"
    assert clause_number.body == "The first condition."
    assert clause_number.numbering_style is NumberingStyle.ROMAN
