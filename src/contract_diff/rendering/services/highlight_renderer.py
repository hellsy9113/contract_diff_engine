from collections.abc import Mapping
from typing import Any

import fitz  # type: ignore[import-untyped]

from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.models.annotation_item import AnnotationItem
from contract_diff.comparison.enums.fragment_operation import FragmentOperation
from contract_diff.comparison.utils.text_diff_helpers import (
    get_changed_fragments,
)
from contract_diff.models.document.bounding_box import BoundingBox
from contract_diff.rendering.styles.pdf_colors import style_for_annotation_type
from contract_diff.rendering.utils.pdf_rects import (
    dedupe_rects,
    merge_nearby_rects,
    rects_are_similar,
    shrink_rect_vertically,
)
from contract_diff.rendering.utils.visual_fragments import prepare_visual_fragments


class HighlightRenderer:
    """
    Draws PDF highlights for added and modified revised-side text.
    """

    def render(
        self,
        pdf_document: Any,
        annotation: AnnotationItem,
        span_boxes: Mapping[str, BoundingBox],
    ) -> tuple[str, ...]:
        if annotation.annotation_type not in {
            AnnotationType.MODIFIED,
            AnnotationType.ADDED,
        }:
            return ()

        if annotation.target is None:
            return (f"{annotation.id}:SKIPPED_HIGHLIGHT_WITHOUT_TARGET",)

        page = self._page(pdf_document, annotation.target.page_number)

        if page is None:
            return (f"{annotation.id}:MISSING_RENDER_TARGET_PAGE",)

        if annotation.annotation_type is AnnotationType.MODIFIED:
            return self._highlight_text_fragments(
                page,
                annotation,
                span_boxes,
                changed_texts=self._modified_changed_texts(annotation),
                fallback_to_spans=False,
            )

        return self._highlight_text_fragments(
            page,
            annotation,
            span_boxes,
            changed_texts=self._added_changed_texts(annotation),
            fallback_to_spans=True,
        )

    def _highlight_target_spans(
        self,
        page: Any,
        annotation: AnnotationItem,
        span_boxes: Mapping[str, BoundingBox],
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        style = style_for_annotation_type(annotation.annotation_type)

        if annotation.target is None:
            return (f"{annotation.id}:SKIPPED_HIGHLIGHT_WITHOUT_TARGET",)

        rects: list[fitz.Rect] = []

        for span_id in annotation.target.source_span_ids:
            bbox = span_boxes.get(span_id)

            if bbox is None:
                warnings.append(f"{annotation.id}:MISSING_SPAN:{span_id}")
                continue

            rects.append(self._rect(bbox))

        rects = self._prepare_rects(rects, annotation)

        if rects:
            self._add_highlight(page, annotation, rects, style)

        return tuple(warnings)

    def _highlight_text_fragments(
        self,
        page: Any,
        annotation: AnnotationItem,
        span_boxes: Mapping[str, BoundingBox],
        changed_texts: list[str],
        fallback_to_spans: bool,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        style = style_for_annotation_type(annotation.annotation_type)
        searched_fragments = self._visual_search_fragments(changed_texts)
        target_boxes = self._target_rects(annotation, span_boxes)
        highlight_rects: list[fitz.Rect] = []

        for fragment in searched_fragments:
            rects = self._search_fragment_rects(page, fragment, target_boxes)

            if not rects:
                warnings.append(f"{annotation.id}:MISSING_FRAGMENT:{fragment}")
                continue

            for rect in rects:
                if any(
                    rects_are_similar(rect, existing) for existing in highlight_rects
                ):
                    continue

                highlight_rects.append(rect)

                if len(highlight_rects) >= style.max_rects:
                    warnings.append(
                        f"{annotation.id}:HIGHLIGHT_RECTS_LIMITED:{style.max_rects}"
                    )
                    break

            if len(highlight_rects) >= style.max_rects:
                break

        if highlight_rects:
            self._add_highlight(page, annotation, highlight_rects, style)
            return tuple(warnings)

        if fallback_to_spans:
            return (
                *tuple(warnings),
                *self._highlight_target_spans(page, annotation, span_boxes),
            )

        if searched_fragments:
            warnings.append(f"{annotation.id}:NO_CHANGED_FRAGMENT_HIGHLIGHTED")
        else:
            warnings.append(f"{annotation.id}:NO_VISUAL_FRAGMENTS")

        return tuple(warnings)

    def _modified_changed_texts(
        self,
        annotation: AnnotationItem,
    ) -> list[str]:
        changed_texts = [
            fragment.revised_text
            for fragment in annotation.fragments
            if fragment.operation is FragmentOperation.INSERTED
            and fragment.revised_text is not None
        ]

        if (
            not changed_texts
            and annotation.original_text is not None
            and annotation.revised_text is not None
        ):
            changed_texts = get_changed_fragments(
                annotation.original_text,
                annotation.revised_text,
            )

        return changed_texts

    def _added_changed_texts(self, annotation: AnnotationItem) -> list[str]:
        if annotation.revised_text is None:
            return []

        return [annotation.revised_text]

    def _visual_search_fragments(self, changed_texts: list[str]) -> tuple[str, ...]:
        fragments: list[str] = []

        for changed_text in changed_texts:
            fragments.extend(prepare_visual_fragments(changed_text))

        return tuple(dict.fromkeys(fragments))

    def _search_fragment_rects(
        self,
        page: Any,
        fragment: str,
        target_boxes: tuple[fitz.Rect, ...],
    ) -> list[fitz.Rect]:
        rects = [
            shrink_rect_vertically(rect)
            for rect in page.search_for(fragment)
            if self._matches_target(rect, target_boxes)
        ]
        return merge_nearby_rects(dedupe_rects(rects))

    def _matches_target(
        self,
        rect: fitz.Rect,
        target_boxes: tuple[fitz.Rect, ...],
    ) -> bool:
        if not target_boxes:
            return True

        return any(rect.intersects(target_box) for target_box in target_boxes)

    def _target_rects(
        self,
        annotation: AnnotationItem,
        span_boxes: Mapping[str, BoundingBox],
    ) -> tuple[fitz.Rect, ...]:
        if annotation.target is None:
            return ()

        return tuple(
            self._rect(span_boxes[span_id])
            for span_id in annotation.target.source_span_ids
            if span_id in span_boxes
        )

    def _prepare_rects(
        self,
        rects: list[fitz.Rect],
        annotation: AnnotationItem,
    ) -> list[fitz.Rect]:
        style = style_for_annotation_type(annotation.annotation_type)
        prepared = merge_nearby_rects(
            dedupe_rects([shrink_rect_vertically(rect) for rect in rects])
        )

        if len(prepared) > style.max_rects:
            return prepared[: style.max_rects]

        return prepared

    def _add_highlight(
        self,
        page: Any,
        annotation: AnnotationItem,
        rects: list[fitz.Rect],
        style: Any,
    ) -> None:
        highlight = page.add_highlight_annot(rects)
        highlight.set_colors(stroke=style.color)
        highlight.set_opacity(style.opacity)
        highlight.set_info(
            title=self._annotation_title(annotation),
            content=self._annotation_content(annotation),
        )
        highlight.update()

    def _annotation_title(self, annotation: AnnotationItem) -> str:
        if annotation.id.startswith("ANN-"):
            return annotation.id

        return f"ANN-{annotation.id}"

    def _annotation_content(self, annotation: AnnotationItem) -> str:
        change_type = annotation.annotation_type.value.title()
        summary = annotation.revised_text or annotation.original_text or ""
        summary = " ".join(summary.split())

        if len(summary) > 140:
            summary = f"{summary[:137]}..."

        return f"{change_type}: {summary}" if summary else change_type

    def _page(self, pdf_document: Any, page_number: int) -> Any | None:
        if page_number < 1 or page_number > pdf_document.page_count:
            return None

        return pdf_document[page_number - 1]

    def _rect(self, bbox: BoundingBox) -> fitz.Rect:
        return fitz.Rect(bbox.x0, bbox.y0, bbox.x1, bbox.y1)
