from __future__ import annotations

import logging
from io import BytesIO
from typing import BinaryIO

from contract_diff.alignment.enums.document_similarity_status import (
    DocumentSimilarityStatus,
)
from contract_diff.alignment.services.alignment_service import AlignmentService
from contract_diff.annotation.services.annotation_builder_service import (
    AnnotationBuilderService,
)
from contract_diff.comparison.enums.change_type import ChangeType
from contract_diff.comparison.models.comparison_result import ComparisonResult
from contract_diff.comparison.services.comparison_service import ComparisonService
from contract_diff.comparison.services.text_unit_comparison_service import (
    TextUnitComparisonService,
)
from contract_diff.core.models.comparison_request import ComparisonRequest
from contract_diff.core.models.engine_result import EngineResult
from contract_diff.core.models.engine_status import EngineStatus
from contract_diff.extraction.readers.pdf.pdf_reader import PdfReader
from contract_diff.extraction.readers.txt.txt_reader import TxtReader
from contract_diff.extraction.registry.reader_registry import ReaderRegistry
from contract_diff.extraction.services.extraction_service import ExtractionService
from contract_diff.models.document.extracted_document import ExtractedDocument
from contract_diff.normalization.models.normalized_document import NormalizedDocument
from contract_diff.normalization.services.normalization_service import (
    NormalizationService,
)
from contract_diff.parsing.models.structured_document import StructuredDocument
from contract_diff.parsing.services.parsing_service import ParsingService
from contract_diff.rendering.services.pdf_rendering_service import PdfRenderingService

logger = logging.getLogger(__name__)


class ContractDiffEngine:
    """
    Coordinates the complete internal contract comparison pipeline.
    """

    def __init__(
        self,
        extraction_service: ExtractionService | None = None,
        normalization_service: NormalizationService | None = None,
        parsing_service: ParsingService | None = None,
        alignment_service: AlignmentService | None = None,
        comparison_service: ComparisonService | None = None,
        text_unit_comparison_service: TextUnitComparisonService | None = None,
        annotation_builder_service: AnnotationBuilderService | None = None,
        rendering_service: PdfRenderingService | None = None,
    ) -> None:
        self._extraction_service = extraction_service or self._default_extraction()
        self._normalization_service = normalization_service or NormalizationService()
        self._parsing_service = parsing_service or ParsingService()
        self._alignment_service = alignment_service or AlignmentService()
        self._comparison_service = comparison_service or ComparisonService()
        self._text_unit_comparison_service = (
            text_unit_comparison_service or TextUnitComparisonService()
        )
        self._annotation_builder_service = (
            annotation_builder_service or AnnotationBuilderService()
        )
        self._rendering_service = rendering_service or PdfRenderingService()

    def compare(
        self,
        original_pdf_stream: bytes | BinaryIO,
        revised_pdf_stream: bytes | BinaryIO,
        original_filename: str = "original.pdf",
        revised_filename: str = "revised.pdf",
    ) -> EngineResult:
        try:
            original_pdf = self._read_bytes(original_pdf_stream)
            revised_pdf = self._read_bytes(revised_pdf_stream)
            request = ComparisonRequest(
                original_pdf=original_pdf,
                revised_pdf=revised_pdf,
                original_filename=original_filename,
                revised_filename=revised_filename,
            )
            return self.compare_request(request)

        except Exception as exc:
            return self._failed_result(exc)

    def compare_request(self, request: ComparisonRequest) -> EngineResult:
        try:
            logger.debug("original bytes: %s", len(request.original_pdf))
            logger.debug("revised bytes: %s", len(request.revised_pdf))

            original_extracted = self._extraction_service.extract(
                BytesIO(request.original_pdf),
                request.original_filename,
            )
            revised_extracted = self._extraction_service.extract(
                BytesIO(request.revised_pdf),
                request.revised_filename,
            )

            original_text = original_extracted.text
            revised_text = revised_extracted.text

            logger.debug("original text chars: %s", len(original_text))
            logger.debug("revised text chars: %s", len(revised_text))
            logger.debug("texts equal: %s", original_text == revised_text)

            original_normalized = self._normalization_service.normalize(
                original_extracted
            )
            revised_normalized = self._normalization_service.normalize(
                revised_extracted
            )
            original_structured = self._parse(original_normalized)
            revised_structured = self._parse(revised_normalized)
            warnings = list(
                self._structured_warnings(original_structured, revised_structured)
            )

            alignment_result = self._alignment_service.align(
                original_structured,
                revised_structured,
            )
            warnings.extend(alignment_result.warnings)

            if alignment_result.status is DocumentSimilarityStatus.REJECTED:
                similarity = alignment_result.document_similarity
                return EngineResult(
                    status=EngineStatus.REJECTED,
                    rendered_document=None,
                    rejection_reason=similarity.reason,
                    message=similarity.message,
                    similarity_score=similarity.overall_score,
                    warnings=self._unique((*warnings, *similarity.warnings)),
                )

            comparison_result = self._comparison_service.compare(
                original_structured,
                revised_structured,
                alignment_result,
            )
            warnings.extend(comparison_result.warnings)
            logger.debug("diff count: %s", self._diff_count(comparison_result))
            self._log_sample_diffs(comparison_result)

            if (
                self._diff_count(comparison_result) == 0
                and original_normalized.text != revised_normalized.text
            ):
                comparison_result = self._text_unit_comparison_service.compare(
                    original_normalized,
                    revised_normalized,
                )
                warnings.extend(comparison_result.warnings)
                logger.debug("diff count: %s", self._diff_count(comparison_result))
                self._log_sample_diffs(comparison_result)

            annotation_plan = self._annotation_builder_service.build(
                comparison_result,
            )
            warnings.extend(annotation_plan.warnings)
            logger.debug("annotation count: %s", len(annotation_plan.annotations))
            logger.debug("output base: revised PDF")

            rendered_document = self._rendering_service.render(
                request.revised_pdf,
                revised_extracted,
                annotation_plan,
            )
            warnings.extend(rendered_document.warnings)
            logger.debug("rendered bytes: %s", len(rendered_document.data))

            return EngineResult(
                status=EngineStatus.SUCCESS,
                rendered_document=rendered_document.model_copy(
                    update={"warnings": self._unique(tuple(warnings))}
                ),
                similarity_score=alignment_result.document_similarity.overall_score,
                warnings=self._unique(tuple(warnings)),
            )

        except Exception as exc:
            return self._failed_result(exc)

    def _structure(self, extracted_document: ExtractedDocument) -> StructuredDocument:
        normalized = self._normalization_service.normalize(extracted_document)
        return self._parse(normalized)

    def _parse(self, normalized_document: NormalizedDocument) -> StructuredDocument:
        return self._parsing_service.parse(normalized_document)

    def _default_extraction(self) -> ExtractionService:
        registry = ReaderRegistry()
        registry.register(PdfReader())
        registry.register(TxtReader())
        return ExtractionService(registry)

    def _read_bytes(self, stream: bytes | BinaryIO) -> bytes:
        if isinstance(stream, bytes):
            return stream

        position = stream.tell()

        try:
            stream.seek(0)
            return stream.read()

        finally:
            stream.seek(position)

    def _structured_warnings(
        self,
        original_document: StructuredDocument,
        revised_document: StructuredDocument,
    ) -> tuple[str, ...]:
        return (
            *original_document.parsing_warnings,
            *revised_document.parsing_warnings,
        )

    def _failed_result(self, exc: Exception) -> EngineResult:
        return EngineResult(
            status=EngineStatus.FAILED,
            rendered_document=None,
            message="Comparison failed.",
            warnings=(f"{exc.__class__.__name__}: {exc}",),
        )

    def _diff_count(self, comparison_result: ComparisonResult) -> int:
        return sum(
            1
            for compared_clause in comparison_result.compared_clauses
            if compared_clause.change_type is not ChangeType.UNCHANGED
        )

    def _log_sample_diffs(self, comparison_result: ComparisonResult) -> None:
        printed = 0

        for compared_clause in comparison_result.compared_clauses:
            if compared_clause.change_type is ChangeType.UNCHANGED:
                continue

            logger.debug(
                "sample diff: %s",
                {
                    "id": compared_clause.id,
                    "change_type": compared_clause.change_type.value,
                    "original_text": compared_clause.original_text,
                    "revised_text": compared_clause.revised_text,
                    "revised_spans": compared_clause.revised_source_span_ids,
                }
            )
            printed += 1

            if printed >= 5:
                return

    def _unique(self, warnings: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        unique_warnings: list[str] = []

        for warning in warnings:
            if warning in seen:
                continue

            seen.add(warning)
            unique_warnings.append(warning)

        return tuple(unique_warnings)
