from contract_diff.comparison.enums.fragment_operation import FragmentOperation
from contract_diff.comparison.services.text_diff_service import TextDiffService


def test_equivalent_uses_alignment_normalization() -> None:
    service = TextDiffService()

    assert service.equivalent(
        "The Buyer shall pay within 30 days.",
        "The   Buyer shall pay\nwithin 30 days.",
    )
    assert service.equivalent(
        "The Buyer shall pay within 30 days.",
        "the Buyer shall pay within 30 days.",
    )
    assert service.equivalent("Grover's algorithm.", "Grover’s algorithm.")


def test_word_level_diff_returns_fragments() -> None:
    service = TextDiffService()

    fragments = service.diff(
        "The Buyer shall pay within 30 days after invoice receipt.",
        "The Buyer shall pay within 45 days.",
    )

    assert fragments[0].text == "The Buyer shall pay within"
    assert any(
        fragment.operation is FragmentOperation.DELETED
        and fragment.original_text == "30"
        for fragment in fragments
    )
    assert any(
        fragment.operation is FragmentOperation.INSERTED
        and fragment.revised_text == "45"
        for fragment in fragments
    )
    assert any(
        fragment.operation is FragmentOperation.EQUAL
        and fragment.text in {"days", "days."}
        for fragment in fragments
    )
    assert any(
        fragment.operation is FragmentOperation.DELETED
        and fragment.original_text == "after invoice receipt"
        for fragment in fragments
    )
