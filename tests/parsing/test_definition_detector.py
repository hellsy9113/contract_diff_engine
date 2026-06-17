from contract_diff.parsing.detectors.definition_detector import DefinitionDetector


def test_detect_quoted_definition() -> None:
    definition = DefinitionDetector.detect(
        '"Agreement" means this contract and all schedules.'
    )

    assert definition is not None
    assert definition.term == "Agreement"
    assert definition.text == '"Agreement" means this contract and all schedules.'


def test_detect_curly_quote_definition() -> None:
    definition = DefinitionDetector.detect(
        "“Confidential Information” means all non-public information."
    )

    assert definition is not None
    assert definition.term == "Confidential Information"


def test_detect_the_term_definition() -> None:
    definition = DefinitionDetector.detect(
        'The term "Services" shall mean implementation services.'
    )

    assert definition is not None
    assert definition.term == "Services"


def test_does_not_detect_plain_clause_as_definition() -> None:
    assert DefinitionDetector.detect("The Buyer shall pay within 30 days.") is None
