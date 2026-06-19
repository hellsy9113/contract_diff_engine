from contract_diff.v3.extraction.clause_extractor import extract_clauses_v3
from contract_diff.v3.models import V3DocumentText, V3PageText


def test_extracts_simple_numbered_clauses() -> None:
    document = V3DocumentText(
        full_text=(
            "1. PAYMENT TERMS\n\n"
            "1.1 The Client shall pay all invoices within 30 days.\n\n"
            "1.2 Payment shall be made by wire transfer."
        ),
        pages=[
            V3PageText(
                page_number=1,
                text=(
                    "1. PAYMENT TERMS\n\n"
                    "1.1 The Client shall pay all invoices within 30 days.\n\n"
                    "1.2 Payment shall be made by wire transfer."
                ),
            )
        ],
    )

    clauses = extract_clauses_v3(document)

    assert [clause.id for clause in clauses] == ["clause-1-1", "clause-1-2"]
    assert [clause.number for clause in clauses] == ["1.1", "1.2"]
    assert [clause.heading for clause in clauses] == ["PAYMENT TERMS", "PAYMENT TERMS"]
    assert clauses[0].text == "1.1 The Client shall pay all invoices within 30 days."
    assert clauses[1].page_number == 1


def test_extracts_numbered_heading_and_child_subclauses() -> None:
    document = V3DocumentText(
        full_text=(
            "4. PAYMENT TERMS\n\n"
            "4.1 The Client shall pay all invoices within 30 days of receipt.\n\n"
            "4.2 Payment shall be made within 30 days of invoice date."
        ),
        pages=[
            V3PageText(
                page_number=1,
                text=(
                    "4. PAYMENT TERMS\n\n"
                    "4.1 The Client shall pay all invoices within 30 days "
                    "of receipt.\n\n"
                    "4.2 Payment shall be made within 30 days of invoice date."
                ),
            )
        ],
    )

    clauses = extract_clauses_v3(document)

    assert len(clauses) == 2
    assert clauses[0].heading == "PAYMENT TERMS"
    assert clauses[1].heading == "PAYMENT TERMS"
    assert clauses[0].order_index == 0
    assert clauses[1].order_index == 1


def test_detects_uppercase_heading_and_attaches_following_clause() -> None:
    document = V3DocumentText(
        full_text=(
            "CONFIDENTIALITY\n\n"
            "8.2 All materials must be returned on termination."
        ),
        pages=[
            V3PageText(
                page_number=2,
                text=(
                    "CONFIDENTIALITY\n\n"
                    "8.2 All materials must be returned on termination."
                ),
            )
        ],
    )

    clauses = extract_clauses_v3(document)

    assert len(clauses) == 1
    assert clauses[0].heading == "CONFIDENTIALITY"
    assert clauses[0].page_number == 2


def test_preserves_multiline_clause_text() -> None:
    document = V3DocumentText(
        full_text=(
            "10.2 Neither party shall be liable for indirect,\n"
            "incidental, or consequential damages."
        ),
        pages=[
            V3PageText(
                page_number=3,
                text=(
                    "10.2 Neither party shall be liable for indirect,\n"
                    "incidental, or consequential damages."
                ),
            )
        ],
    )

    clauses = extract_clauses_v3(document)

    assert len(clauses) == 1
    assert clauses[0].text == (
        "10.2 Neither party shall be liable for indirect, incidental, "
        "or consequential damages."
    )


def test_falls_back_to_paragraph_chunks_when_no_numbering_exists() -> None:
    document = V3DocumentText(
        full_text=(
            "This Agreement begins on the effective date.\n\n"
            "Payment is due within thirty days."
        ),
        pages=[
            V3PageText(
                page_number=1,
                text=(
                    "This Agreement begins on the effective date.\n\n"
                    "Payment is due within thirty days."
                ),
            )
        ],
    )

    clauses = extract_clauses_v3(document)

    assert [clause.id for clause in clauses] == ["clause-0001", "clause-0002"]
    assert [clause.number for clause in clauses] == [None, None]
    assert clauses[0].text == "This Agreement begins on the effective date."
    assert clauses[1].text == "Payment is due within thirty days."
