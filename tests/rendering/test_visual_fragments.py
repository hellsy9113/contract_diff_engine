from contract_diff.rendering.utils.visual_fragments import prepare_visual_fragments


def test_fragment_filtering_keeps_meaningful_phrases() -> None:
    fragments = prepare_visual_fragments(
        "the difficulty of solving systems of quadratic equations"
    )

    assert "difficulty of solving systems" in fragments
    assert "systems of quadratic equations" in fragments
    assert "the" not in fragments
    assert "of" not in fragments


def test_full_paragraph_is_not_first_visual_choice() -> None:
    paragraph = (
        "Multivariate cryptography is built on the difficulty of solving "
        "systems of quadratic equations, an NP-hard problem."
    )

    fragments = prepare_visual_fragments(paragraph)

    assert fragments
    assert paragraph not in fragments
    assert all(len(fragment.split()) <= 4 for fragment in fragments)


def test_short_common_words_are_ignored_but_numeric_changes_survive() -> None:
    assert prepare_visual_fragments("the") == []
    assert prepare_visual_fragments("45") == ["45"]
