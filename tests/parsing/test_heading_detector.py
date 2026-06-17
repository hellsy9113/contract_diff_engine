from contract_diff.parsing.detectors.heading_detector import HeadingDetector
from contract_diff.parsing.enums.numbering_style import NumberingStyle


def test_detect_numbered_heading() -> None:
    heading = HeadingDetector.detect("1. Definitions")

    assert heading is not None
    assert heading.number == "1"
    assert heading.title == "Definitions"
    assert heading.numbering_style is NumberingStyle.DECIMAL


def test_detect_article_heading() -> None:
    heading = HeadingDetector.detect("ARTICLE 2 - PAYMENT")

    assert heading is not None
    assert heading.number == "2"
    assert heading.title == "PAYMENT"
    assert heading.numbering_style is NumberingStyle.ARTICLE


def test_detect_section_heading() -> None:
    heading = HeadingDetector.detect("SECTION 5. TERMINATION")

    assert heading is not None
    assert heading.number == "5"
    assert heading.title == "TERMINATION"
    assert heading.numbering_style is NumberingStyle.SECTION


def test_does_not_detect_clause_as_heading() -> None:
    assert HeadingDetector.detect("1.1 First clause") is None
