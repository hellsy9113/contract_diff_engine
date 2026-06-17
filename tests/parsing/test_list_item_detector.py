from contract_diff.parsing.detectors.list_item_detector import ListItemDetector
from contract_diff.parsing.enums.numbering_style import NumberingStyle


def test_detect_letter_list_item() -> None:
    list_item = ListItemDetector.detect("(a) first item")

    assert list_item is not None
    assert list_item.marker == "(a)"
    assert list_item.body == "first item"
    assert list_item.numbering_style is NumberingStyle.LETTER


def test_detect_roman_list_item() -> None:
    list_item = ListItemDetector.detect("(ii) second item")

    assert list_item is not None
    assert list_item.marker == "(ii)"
    assert list_item.body == "second item"
    assert list_item.numbering_style is NumberingStyle.ROMAN


def test_detect_bullet_list_item() -> None:
    list_item = ListItemDetector.detect("- bullet item")

    assert list_item is not None
    assert list_item.marker == "-"
    assert list_item.body == "bullet item"
    assert list_item.numbering_style is NumberingStyle.BULLET


def test_does_not_detect_plain_text_as_list_item() -> None:
    assert ListItemDetector.detect("plain paragraph text") is None
