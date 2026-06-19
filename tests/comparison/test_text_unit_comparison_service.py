from contract_diff.comparison.enums.change_type import ChangeType
from contract_diff.comparison.services.text_unit_comparison_service import (
    TextUnitComparisonService,
)
from contract_diff.comparison.utils.text_diff_helpers import get_changed_fragments
from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.models.document.metadata import DocumentMetadata
from contract_diff.normalization.models.normalized_document import NormalizedDocument
from contract_diff.normalization.models.normalized_page import NormalizedPage
from contract_diff.normalization.models.normalized_text_unit import (
    NormalizedTextUnit,
)


def test_text_unit_comparison_detects_inserted_revised_lines() -> None:
    original = make_document(
        (
            make_unit("orig-1", "Introduction"),
            make_unit("orig-2", "Quantum search is discussed."),
        )
    )
    revised = make_document(
        (
            make_unit("rev-1", "Introduction"),
            make_unit("rev-2", "Quantum search is discussed."),
            make_unit("rev-3", "Grover's algorithm speeds unstructured search."),
        )
    )

    result = TextUnitComparisonService().compare(original, revised)

    assert result.summary.added == 1
    assert result.warnings == ("LINE_LEVEL_FALLBACK_COMPARISON",)
    compared = result.compared_clauses[0]
    assert compared.change_type is ChangeType.ADDED
    assert compared.revised_text == "Grover's algorithm speeds unstructured search."
    assert compared.revised_source_span_ids == ("span-rev-3",)


def test_text_unit_comparison_detects_modified_revised_lines() -> None:
    original = make_document(
        (make_unit("orig-1", "Payment shall be made within 30 days."),)
    )
    revised = make_document(
        (make_unit("rev-1", "Payment shall be made within 45 days."),)
    )

    result = TextUnitComparisonService().compare(original, revised)

    assert result.summary.modified == 1
    compared = result.compared_clauses[0]
    assert compared.change_type is ChangeType.MODIFIED
    assert compared.original_text == "Payment shall be made within 30 days."
    assert compared.revised_text == "Payment shall be made within 45 days."
    assert compared.revised_source_span_ids == ("span-rev-1",)
    assert compared.fragments


def test_changed_fragments_exclude_unchanged_text_inside_modified_line() -> None:
    fragments = get_changed_fragments(
        "The tenant shall pay rent on the first day of each month.",
        "The tenant shall pay rent on the fifth day of each month.",
    )

    assert fragments == ["fifth"]


def test_insertion_inside_long_paragraph_does_not_return_full_paragraph() -> None:
    fragments = get_changed_fragments(
        ("Sentence one remains. Sentence two remains. Sentence three remains."),
        (
            "Sentence one remains. Added sentence appears here. "
            "Sentence two remains. Sentence three remains."
        ),
    )

    assert fragments == ["Added sentence appears here"]


def test_pagination_shift_is_aligned_globally_without_false_modifications() -> None:
    original = make_document(
        (
            make_unit("orig-1", "Stable paragraph one."),
            make_unit("orig-2", "Stable paragraph two."),
            make_unit("orig-3", "Stable paragraph three."),
        )
    )
    revised = make_document(
        (
            make_unit("rev-0", "New intro paragraph."),
            make_unit("rev-1", "Stable paragraph one."),
            make_unit("rev-2", "Stable paragraph two."),
            make_unit("rev-3", "Stable paragraph three."),
        )
    )

    result = TextUnitComparisonService().compare(original, revised)

    assert result.summary.added == 1
    assert result.summary.modified == 0
    assert result.summary.removed == 0


def test_similar_replace_becomes_modification() -> None:
    original = make_document((make_unit("orig-1", "Payment is due within 30 days."),))
    revised = make_document((make_unit("rev-1", "Payment is due within 45 days."),))

    result = TextUnitComparisonService().compare(original, revised)

    assert result.summary.modified == 1
    assert result.summary.added == 0
    assert result.summary.removed == 0


def test_unrelated_replace_becomes_delete_and_insert() -> None:
    original = make_document(
        (make_unit("orig-1", "The tenant shall maintain insurance."),)
    )
    revised = make_document(
        (make_unit("rev-1", "This agreement is governed by Indian law."),)
    )

    result = TextUnitComparisonService().compare(original, revised)

    assert result.summary.modified == 0
    assert result.summary.added == 1
    assert result.summary.removed == 1


def test_whitespace_only_changes_are_ignored() -> None:
    original = make_document((make_unit("orig-1", "Payment is due within 30 days."),))
    revised = make_document((make_unit("rev-1", "Payment   is due\nwithin 30 days."),))

    result = TextUnitComparisonService().compare(original, revised)

    assert result.compared_clauses == ()
    assert result.summary.total == 0


def test_smart_quote_changes_are_ignored() -> None:
    original = make_document((make_unit("orig-1", "Grover's algorithm."),))
    revised = make_document((make_unit("rev-1", "Grover’s algorithm."),))

    result = TextUnitComparisonService().compare(original, revised)

    assert result.compared_clauses == ()
    assert result.summary.total == 0


def make_document(
    units: tuple[NormalizedTextUnit, ...],
) -> NormalizedDocument:
    return NormalizedDocument(
        format=DocumentFormat.PDF,
        metadata=DocumentMetadata(
            filename="contract.pdf",
            extension=".pdf",
            size_bytes=100,
            page_count=1,
        ),
        pages=(
            NormalizedPage(
                id="normalized-page-1",
                page_number=1,
                source_page_id="page-1",
                units=units,
            ),
        ),
    )


def make_unit(unit_id: str, text: str) -> NormalizedTextUnit:
    return NormalizedTextUnit(
        id=unit_id,
        text=text,
        page_number=1,
        source_page_id="page-1",
        source_block_id=f"block-{unit_id}",
        source_line_ids=(f"line-{unit_id}",),
        source_span_ids=(f"span-{unit_id}",),
    )
