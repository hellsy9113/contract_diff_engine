from __future__ import annotations

import fitz  # type: ignore[import-untyped]

from contract_diff.extraction.structured.pipeline import extract_and_process_pdf
from contract_diff.extraction.structured.word_stream import build_document_word_stream


def test_multi_page_document_produces_one_continuous_word_stream() -> None:
    document = extract_and_process_pdf(
        _text_pdf(["First page clause.", "Second page clause."])
    )

    stream = build_document_word_stream(
        document,
        source_file_name="contract.pdf",
    )

    assert stream.source_file_name == "contract.pdf"
    assert [token.text for token in stream.tokens] == [
        "First",
        "page",
        "clause.",
        "Second",
        "page",
        "clause.",
    ]
    assert [token.token_index for token in stream.tokens] == list(
        range(len(stream.tokens))
    )
    assert stream.pages[0].token_start_index == 0
    assert stream.pages[0].token_end_index == 3
    assert stream.pages[1].token_start_index == 3
    assert stream.pages[1].token_end_index == 6


def test_page_shifted_content_can_match_as_document_level_stream() -> None:
    original = build_document_word_stream(
        extract_and_process_pdf(
            _text_pdf(["Intro moved clause continues.", "Tail section."])
        )
    )
    revised = build_document_word_stream(
        extract_and_process_pdf(
            _text_pdf(["Intro", "moved clause continues. Tail section."])
        )
    )

    assert [token.normalized for token in original.tokens] == [
        token.normalized for token in revised.tokens
    ]

    revised_moved_token = revised.tokens[1]
    assert revised_moved_token.text == "moved"
    assert revised_moved_token.page_number == 2


def test_word_stream_does_not_lose_punctuation_heavy_words() -> None:
    stream = build_document_word_stream(
        extract_and_process_pdf(
            _text_pdf(["Buyer shall pay $1,000.00; deadline: 01/31/2026."])
        )
    )

    assert "$1,000.00;" in [token.text for token in stream.tokens]
    assert "deadline:" in [token.text for token in stream.tokens]
    assert "01/31/2026." in [token.text for token in stream.tokens]


def test_word_stream_can_reconstruct_readable_text() -> None:
    stream = build_document_word_stream(
        extract_and_process_pdf(_text_pdf(["Buyer shall pay within 30 days."]))
    )

    assert stream.slice_text(0, len(stream.tokens)) == (
        "Buyer shall pay within 30 days."
    )
    assert stream.slice_tokens(1, 4) == stream.tokens[1:4]
    assert stream.get_token(0).text == "Buyer"
    assert (
        stream.find_nearest_surviving_anchor(3, frozenset({0, 4})) == (stream.tokens[4])
    )


def _text_pdf(page_texts: list[str]) -> bytes:
    document = fitz.open()

    for page_text in page_texts:
        page = document.new_page(width=500, height=500)
        page.insert_text((72, 72), page_text, fontsize=11)

    data = bytes(document.tobytes())
    document.close()
    return data
