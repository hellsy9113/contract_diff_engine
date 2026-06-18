from __future__ import annotations

from contract_diff.extraction.structured.sections import assign_section_paths
from tests.extraction.structured.helpers import make_block, make_document, make_page


def test_simple_heading_path_is_assigned_to_following_block() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block(
                        "2. Confidentiality",
                        block_index=0,
                        block_type="heading",
                    ),
                    make_block(
                        "The receiving party shall protect information.",
                        block_index=1,
                        block_type="paragraph",
                    ),
                ]
            )
        ]
    )

    assigned = assign_section_paths(document)

    assert assigned.pages[0].blocks[1].section_path == ["2. Confidentiality"]


def test_nested_heading_path_is_assigned() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block(
                        "2. Confidentiality",
                        block_index=0,
                        block_type="heading",
                    ),
                    make_block("2.1 Exceptions", block_index=1, block_type="heading"),
                    make_block(
                        "Confidential information does not include public data.",
                        block_index=2,
                        block_type="paragraph",
                    ),
                ]
            )
        ]
    )

    assigned = assign_section_paths(document)

    assert assigned.pages[0].blocks[2].section_path == [
        "2. Confidentiality",
        "2.1 Exceptions",
    ]


def test_article_heading_path_is_assigned() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block("ARTICLE IV", block_index=0, block_type="heading"),
                    make_block(
                        "The parties agree.",
                        block_index=1,
                        block_type="paragraph",
                    ),
                ]
            )
        ]
    )

    assigned = assign_section_paths(document)

    assert assigned.pages[0].blocks[1].section_path == ["ARTICLE IV"]


def test_exhibit_and_schedule_headings_reset_top_level_path() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block("EXHIBIT A", block_index=0, block_type="heading"),
                    make_block("Exhibit text.", block_index=1, block_type="paragraph"),
                    make_block("SCHEDULE 1", block_index=2, block_type="heading"),
                    make_block("Schedule text.", block_index=3, block_type="paragraph"),
                ]
            )
        ]
    )

    assigned = assign_section_paths(document)

    assert assigned.pages[0].blocks[1].section_path == ["EXHIBIT A"]
    assert assigned.pages[0].blocks[3].section_path == ["SCHEDULE 1"]


def test_blocks_before_first_heading_have_empty_section_path() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block("Intro text.", block_index=0, block_type="paragraph"),
                    make_block("1. Terms", block_index=1, block_type="heading"),
                    make_block("Term text.", block_index=2, block_type="paragraph"),
                ]
            )
        ]
    )

    assigned = assign_section_paths(document)

    assert assigned.pages[0].blocks[0].section_path == []
    assert assigned.pages[0].blocks[2].section_path == ["1. Terms"]


def test_section_path_survives_multi_page_extraction() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block(
                        "5. Payment",
                        page_index=0,
                        block_index=0,
                        block_type="heading",
                    )
                ],
                page_index=0,
            ),
            make_page(
                [
                    make_block(
                        "The buyer shall pay promptly.",
                        page_index=1,
                        block_index=0,
                        block_type="paragraph",
                    )
                ],
                page_index=1,
            ),
        ]
    )

    assigned = assign_section_paths(document)

    assert assigned.pages[1].blocks[0].section_path == ["5. Payment"]
