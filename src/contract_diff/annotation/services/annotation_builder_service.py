from contract_diff.annotation.enums.annotation_type import AnnotationType
from contract_diff.annotation.enums.highlight_style import HighlightStyle
from contract_diff.annotation.models.annotation_appendix_entry import (
    AnnotationAppendixEntry,
)
from contract_diff.annotation.models.annotation_item import AnnotationItem
from contract_diff.annotation.models.annotation_plan import (
    AnnotationPlan,
    AnnotationSummary,
)
from contract_diff.annotation.services.annotation_id_service import AnnotationIdService
from contract_diff.annotation.services.annotation_target_resolver import (
    AnnotationTargetResolver,
)
from contract_diff.comparison.enums.change_type import ChangeType
from contract_diff.comparison.models.compared_clause import ComparedClause
from contract_diff.comparison.models.comparison_result import ComparisonResult


class AnnotationBuilderService:
    """
    Converts comparison output into renderer-facing annotation plans.
    """

    def __init__(
        self,
        annotation_id_service: AnnotationIdService | None = None,
        target_resolver: AnnotationTargetResolver | None = None,
    ) -> None:
        self._annotation_id_service = annotation_id_service or AnnotationIdService()
        self._target_resolver = target_resolver or AnnotationTargetResolver()

    def build(self, comparison_result: ComparisonResult) -> AnnotationPlan:
        annotations = tuple(
            self._annotation_for(compared_clause)
            for compared_clause in comparison_result.compared_clauses
            if compared_clause.change_type is not ChangeType.UNCHANGED
        )
        appendix_entries = tuple(
            self._appendix_entry_for(annotation) for annotation in annotations
        )
        warnings = self._warnings(comparison_result, annotations)

        return AnnotationPlan(
            annotations=annotations,
            appendix_entries=appendix_entries,
            summary=self._summary(annotations),
            warnings=warnings,
        )

    def _annotation_for(self, compared_clause: ComparedClause) -> AnnotationItem:
        annotation_type = self._annotation_type(compared_clause.change_type)
        target, target_warnings = self._target_resolver.resolve(compared_clause)
        warnings = (*compared_clause.warnings, *target_warnings)
        page_number = target.page_number if target is not None else None

        return AnnotationItem(
            id=self._annotation_id_service.next_id(),
            annotation_type=annotation_type,
            style=self._style(annotation_type),
            target=target,
            original_text=compared_clause.original_text,
            revised_text=compared_clause.revised_text,
            popup_text=self._popup_text(annotation_type, compared_clause),
            heading=compared_clause.heading,
            page_number=page_number,
            fragments=compared_clause.fragments,
            warnings=warnings,
        )

    def _appendix_entry_for(
        self,
        annotation: AnnotationItem,
    ) -> AnnotationAppendixEntry:
        return AnnotationAppendixEntry(
            annotation_id=annotation.id,
            annotation_type=annotation.annotation_type,
            page_number=annotation.page_number,
            heading=annotation.heading,
            original_text=annotation.original_text,
            revised_text=annotation.revised_text,
            notes=annotation.warnings,
        )

    def _annotation_type(self, change_type: ChangeType) -> AnnotationType:
        if change_type is ChangeType.MODIFIED:
            return AnnotationType.MODIFIED

        if change_type is ChangeType.ADDED:
            return AnnotationType.ADDED

        return AnnotationType.REMOVED

    def _style(self, annotation_type: AnnotationType) -> HighlightStyle:
        if annotation_type is AnnotationType.MODIFIED:
            return HighlightStyle.MODIFIED_HIGHLIGHT

        if annotation_type is AnnotationType.ADDED:
            return HighlightStyle.ADDED_HIGHLIGHT

        return HighlightStyle.REMOVED_MARKER

    def _popup_text(
        self,
        annotation_type: AnnotationType,
        compared_clause: ComparedClause,
    ) -> str:
        if annotation_type is AnnotationType.ADDED:
            return "Not present in original document"

        return compared_clause.original_text or ""

    def _summary(
        self,
        annotations: tuple[AnnotationItem, ...],
    ) -> AnnotationSummary:
        return AnnotationSummary(
            total=len(annotations),
            modified=self._count(annotations, AnnotationType.MODIFIED),
            added=self._count(annotations, AnnotationType.ADDED),
            removed=self._count(annotations, AnnotationType.REMOVED),
            unresolved=sum(
                1 for annotation in annotations if annotation.target is None
            ),
        )

    def _count(
        self,
        annotations: tuple[AnnotationItem, ...],
        annotation_type: AnnotationType,
    ) -> int:
        return sum(
            1
            for annotation in annotations
            if annotation.annotation_type is annotation_type
        )

    def _warnings(
        self,
        comparison_result: ComparisonResult,
        annotations: tuple[AnnotationItem, ...],
    ) -> tuple[str, ...]:
        warnings = (
            *comparison_result.warnings,
            *(warning for item in annotations for warning in item.warnings),
        )
        return self._unique(warnings)

    def _unique(self, warnings: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        unique_warnings: list[str] = []

        for warning in warnings:
            if warning in seen:
                continue

            seen.add(warning)
            unique_warnings.append(warning)

        return tuple(unique_warnings)
