import fitz  # type: ignore[import-untyped]

from contract_diff.rendering.utils.visual_diagnostics import (
    collect_visual_diagnostics,
)


def test_visual_diagnostics_reports_annotation_counts() -> None:
    document = fitz.open()
    page = document.new_page(width=300, height=300)
    page.insert_text((40, 80), "Changed text appears here.", fontsize=12)
    highlight = page.add_highlight_annot(fitz.Rect(40, 66, 180, 84))
    highlight.update()

    diagnostics = collect_visual_diagnostics(document)

    assert diagnostics.total_highlights == 1
    assert diagnostics.highlight_annotations_by_page == {1: 1}
    assert diagnostics.annotation_counts.get("Text", 0) == 0
    assert diagnostics.annotation_counts.get("Square", 0) == 0
    document.close()


def test_visual_diagnostics_reports_dense_pages() -> None:
    document = fitz.open()
    page = document.new_page(width=300, height=300)

    for index in range(12):
        y0 = 20 + (index * 18)
        highlight = page.add_highlight_annot(fitz.Rect(20, y0, 280, y0 + 12))
        highlight.update()

    diagnostics = collect_visual_diagnostics(document, dense_area_threshold=0.18)

    assert diagnostics.max_highlights_on_one_page == 12
    assert diagnostics.dense_pages == (1,)
    document.close()
