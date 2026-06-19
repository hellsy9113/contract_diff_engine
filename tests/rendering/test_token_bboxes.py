from __future__ import annotations

from contract_diff.extraction.structured.models import WordToken
from contract_diff.extraction.structured.word_tokens import normalize_word_token_text
from contract_diff.rendering.utils.token_bboxes import group_changed_token_bboxes


def test_single_changed_word_creates_one_small_rect() -> None:
    rects = group_changed_token_bboxes([make_token("must", x0=100, x1=124)])

    assert len(rects) == 1
    assert float(rects[0].width) < 32


def test_two_adjacent_inserted_words_create_one_compact_rect() -> None:
    rects = group_changed_token_bboxes(
        [
            make_token("on", x0=100, x1=114),
            make_token("time", x0=116, x1=142),
        ]
    )

    assert len(rects) == 1
    assert float(rects[0].width) < 50


def test_changed_words_on_two_lines_create_two_rectangles() -> None:
    rects = group_changed_token_bboxes(
        [
            make_token("security", x0=100, x1=150, line_id="line-1"),
            make_token("features", x0=72, x1=120, y0=92, y1=104, line_id="line-2"),
        ]
    )

    assert len(rects) == 2
    assert float(rects[0].y0) != float(rects[1].y0)


def make_token(
    text: str,
    *,
    x0: float,
    x1: float,
    y0: float = 72,
    y1: float = 84,
    line_id: str = "line-1",
) -> WordToken:
    return WordToken(
        id=f"token-{text}",
        text=text,
        normalized=normalize_word_token_text(text),
        page_number=1,
        bbox=(x0, y0, x1, y1),
        line_id=line_id,
        block_id="page-0-block-0",
        paragraph_id="page-0-block-0",
        section_heading=None,
        token_index=0,
    )
