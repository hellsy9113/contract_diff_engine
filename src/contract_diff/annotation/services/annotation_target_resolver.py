from contract_diff.annotation.models.annotation_target import (
    AnchorType,
    AnnotationTarget,
)
from contract_diff.comparison.enums.change_type import ChangeType
from contract_diff.comparison.models.compared_clause import ComparedClause


class AnnotationTargetResolver:
    """
    Resolves comparison records to revised-document annotation targets.
    """

    def resolve(
        self,
        compared_clause: ComparedClause,
    ) -> tuple[AnnotationTarget | None, tuple[str, ...]]:
        clause_id = self._target_clause_id(compared_clause)
        page_number = compared_clause.revised_page_number
        source_span_ids = self._source_span_ids(compared_clause)
        anchor_type = self._anchor_type(compared_clause)
        warnings: tuple[str, ...] = ()

        if clause_id is None:
            warnings = (*warnings, "MISSING_ANNOTATION_TARGET_CLAUSE")

        if page_number is None:
            warnings = (*warnings, "MISSING_ANNOTATION_TARGET_PAGE")

        if not source_span_ids:
            warnings = (*warnings, "MISSING_ANNOTATION_TARGET_SPANS")

        if clause_id is None or page_number is None:
            return None, warnings

        return (
            AnnotationTarget(
                clause_id=clause_id,
                page_number=page_number,
                source_span_ids=source_span_ids,
                anchor_type=anchor_type,
            ),
            warnings,
        )

    def _target_clause_id(self, compared_clause: ComparedClause) -> str | None:
        if compared_clause.change_type is ChangeType.REMOVED:
            return compared_clause.revised_anchor_clause_id

        return compared_clause.revised_clause_id

    def _source_span_ids(
        self,
        compared_clause: ComparedClause,
    ) -> tuple[str, ...]:
        return compared_clause.revised_source_span_ids

    def _anchor_type(self, compared_clause: ComparedClause) -> AnchorType:
        if compared_clause.change_type is ChangeType.REMOVED:
            return "revised_anchor_clause"

        return "revised_clause"
