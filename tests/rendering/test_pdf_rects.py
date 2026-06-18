import fitz  # type: ignore[import-untyped]

from contract_diff.rendering.utils.pdf_rects import dedupe_rects, rects_are_similar


def test_dedupe_rects_removes_similar_rectangles() -> None:
    rects = [
        fitz.Rect(10, 10, 50, 20),
        fitz.Rect(10.5, 10.5, 50.5, 20.5),
        fitz.Rect(80, 10, 120, 20),
    ]

    deduped = dedupe_rects(rects)

    assert len(deduped) == 2
    assert rects_are_similar(deduped[0], rects[0])
    assert rects_are_similar(deduped[1], rects[2])
