from __future__ import annotations

import fitz  # type: ignore[import-untyped]

from contract_diff.extraction.structured.pipeline import (
    extract_and_process_pdf,
    get_document_comparison_blocks,
    get_document_comparison_text,
    process_structured_document,
)
from tests.extraction.structured.helpers import make_block, make_document, make_page


def test_pipeline_works_on_simple_pdf() -> None:
    document = extract_and_process_pdf(_text_pdf(["1. Payment Terms", "Buyer pays."]))

    assert document.page_count == 1
    assert get_document_comparison_blocks(document)


def test_pipeline_removes_headers_and_footers_from_comparison_text() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block("Shared Header", page_index=0, y0=20),
                    make_block(
                        "The buyer shall pay promptly.",
                        page_index=0,
                        block_index=1,
                        y0=120,
                    ),
                    make_block("1", page_index=0, block_index=2, y0=650),
                ],
                page_index=0,
            ),
            make_page(
                [
                    make_block("Shared Header", page_index=1, y0=20),
                    make_block(
                        "The seller shall deliver promptly.",
                        page_index=1,
                        block_index=1,
                        y0=120,
                    ),
                    make_block("2", page_index=1, block_index=2, y0=650),
                ],
                page_index=1,
            ),
        ]
    )

    processed = process_structured_document(document)
    comparison_text = get_document_comparison_text(processed)

    assert "Shared Header" not in comparison_text
    assert "The buyer shall pay promptly." in comparison_text
    assert "The seller shall deliver promptly." in comparison_text


def test_pipeline_assigns_block_types() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block("1. Payment Terms", block_index=0),
                    make_block(
                        "The buyer shall pay within thirty days.",
                        block_index=1,
                    ),
                ]
            )
        ]
    )

    processed = process_structured_document(document)

    assert [block.block_type for block in processed.pages[0].blocks] == [
        "heading",
        "paragraph",
    ]


def test_pipeline_assigns_section_paths() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block("2. Confidentiality", block_index=0),
                    make_block(
                        "The receiving party shall protect information.",
                        block_index=1,
                    ),
                ]
            )
        ]
    )

    processed = process_structured_document(document)

    assert processed.pages[0].blocks[1].section_path == ["2. Confidentiality"]


def test_pipeline_detects_columns_in_synthetic_two_column_document() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block("Left 1", block_index=0, x0=72, x1=180, y0=100),
                    make_block("Right 1", block_index=1, x0=300, x1=430, y0=100),
                    make_block("Left 2", block_index=2, x0=72, x1=180, y0=140),
                    make_block("Right 2", block_index=3, x0=300, x1=430, y0=140),
                ]
            )
        ]
    )

    processed = process_structured_document(document)

    assert [block.column_index for block in processed.pages[0].blocks] == [
        0,
        0,
        1,
        1,
    ]


def test_pipeline_does_not_crash_on_empty_low_text_pdf() -> None:
    document = extract_and_process_pdf(_empty_pdf())

    assert document.page_count == 1
    assert "PDF has very little extractable text" in document.warnings


def test_pipeline_returns_profiler_warnings() -> None:
    document = extract_and_process_pdf(_empty_pdf())

    assert document.warnings


def _text_pdf(page_texts: list[str]) -> bytes:
    document = fitz.open()
    page = document.new_page(width=400, height=400)
    y = 72

    for text in page_texts:
        page.insert_text((72, y), text, fontsize=11)
        y += 32

    data = bytes(document.tobytes())
    document.close()
    return data


def _empty_pdf() -> bytes:
    document = fitz.open()
    document.new_page(width=400, height=400)
    data = bytes(document.tobytes())
    document.close()
    return data
