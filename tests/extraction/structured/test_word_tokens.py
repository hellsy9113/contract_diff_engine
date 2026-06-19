from __future__ import annotations

import fitz  # type: ignore[import-untyped]

from contract_diff.extraction.structured.models import (
    BoundingBox,
    ExtractedWord,
)
from contract_diff.extraction.structured.pipeline import extract_and_process_pdf
from contract_diff.extraction.structured.word_tokens import (
    build_word_tokens,
    normalize_word_token_text,
)
from tests.extraction.structured.helpers import make_block, make_document, make_page


def test_extracts_word_tokens_from_pdf_page() -> None:
    document = extract_and_process_pdf(_text_pdf(["Payment terms apply."]))

    assert document.word_tokens
    assert [token.text for token in document.word_tokens[:3]] == [
        "Payment",
        "terms",
        "apply.",
    ]


def test_word_token_order_follows_natural_reading_order() -> None:
    document = extract_and_process_pdf(
        _text_pdf(["First line words.", "Second line words."])
    )

    assert [token.text for token in document.word_tokens[:6]] == [
        "First",
        "line",
        "words.",
        "Second",
        "line",
        "words.",
    ]
    assert [token.token_index for token in document.word_tokens] == list(
        range(len(document.word_tokens))
    )


def test_word_token_has_page_number_and_bbox() -> None:
    document = extract_and_process_pdf(_text_pdf(["Payment terms apply."]))
    token = document.word_tokens[0]

    assert token.page_number == 1
    assert len(token.bbox) == 4
    assert token.bbox[2] > token.bbox[0]
    assert token.bbox[3] > token.bbox[1]


def test_word_token_preserves_original_display_text() -> None:
    document = extract_and_process_pdf(_text_pdf(["Payment terms apply."]))

    assert document.word_tokens[2].text == "apply."
    assert document.word_tokens[2].normalized == "apply."


def test_word_token_normalizes_text_for_matching() -> None:
    assert normalize_word_token_text("  Buyer\u2019s   obligations  ") == (
        "buyer's obligations"
    )
    assert normalize_word_token_text("Section\u20115") == "section-5"


def test_empty_no_text_pdf_does_not_crash() -> None:
    document = extract_and_process_pdf(_empty_pdf())

    assert document.page_count == 1
    assert document.word_tokens == []


def test_word_tokens_preserve_section_heading_when_available() -> None:
    document = make_document(
        [
            make_page(
                [
                    make_block(
                        "The buyer shall pay.",
                        block_type="paragraph",
                        section_path=["2. Payment Terms"],
                    )
                ]
            ).model_copy(
                update={
                    "words": [
                        _word(
                            text="The",
                            word_index=0,
                        ),
                        _word(
                            text="buyer",
                            word_index=1,
                        ),
                    ]
                }
            )
        ]
    )

    tokens = build_word_tokens(document)

    assert [token.section_heading for token in tokens] == [
        "2. Payment Terms",
        "2. Payment Terms",
    ]
    assert tokens[0].paragraph_id == "page-0-block-0"


def _word(
    *,
    text: str,
    word_index: int,
) -> ExtractedWord:
    return ExtractedWord(
        text=text,
        bbox=BoundingBox(
            x0=72 + word_index * 20,
            y0=72,
            x1=90 + word_index * 20,
            y1=84,
        ),
        page_index=0,
        word_index=word_index,
        block_index=0,
        line_index=0,
    )


def _text_pdf(lines: list[str]) -> bytes:
    document = fitz.open()
    page = document.new_page(width=400, height=400)
    y = 72

    for line in lines:
        page.insert_text((72, y), line, fontsize=11)
        y += 28

    data = bytes(document.tobytes())
    document.close()
    return data


def _empty_pdf() -> bytes:
    document = fitz.open()
    document.new_page(width=400, height=400)
    data = bytes(document.tobytes())
    document.close()
    return data
