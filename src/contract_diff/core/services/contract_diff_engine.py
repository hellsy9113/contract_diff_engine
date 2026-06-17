from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

from contract_diff.alignment.enums.document_similarity_status import (
    DocumentSimilarityStatus,
)
from contract_diff.alignment.services.alignment_service import AlignmentService
from contract_diff.annotation.services.annotation_builder_service import (
    AnnotationBuilderService,
)
from contract_diff.comparison.services.comparison_service import ComparisonService
from contract_diff.core.models.comparison_request import ComparisonRequest
from contract_diff.core.models.engine_result import EngineResult
from contract_diff.core.models.engine_status import EngineStatus
from contract_diff.extraction.readers.pdf.pdf_reader import PdfReader
from contract_diff.extraction.readers.txt.txt_reader import TxtReader
from contract_diff.extraction.registry.reader_registry import ReaderRegistry
from contract_diff.extraction.services.extraction_service import ExtractionService
from contract_diff.models.document.extracted_document import ExtractedDocument
from contract_diff.normalization.services.normalization_service import (
    NormalizationService,
)
from contract_diff.parsing.models.structured_document import StructuredDocument
from contract_diff.parsing.services.parsing_service import ParsingService
from contract_diff.rendering.services.pdf_rendering_service import PdfRenderingService


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
        annotation_builder_service: AnnotationBuilderService | None = None,
        rendering_service: PdfRenderingService | None = None,
    ) -> None:
        self._extraction_service = extraction_service or self._default_extraction()
        self._normalization_service = normalization_service or NormalizationService()
        self._parsing_service = parsing_service or ParsingService()
        self._alignment_service = alignment_service or AlignmentService()
        self._comparison_service = comparison_service or ComparisonService()
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
            original_extracted = self._extraction_service.extract(
                BytesIO(request.original_pdf),
                request.original_filename,
            )
            revised_extracted = self._extraction_service.extract(
                BytesIO(request.revised_pdf),
                request.revised_filename,
            )

            original_structured = self._structure(original_extracted)
            revised_structured = self._structure(revised_extracted)
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

            annotation_plan = self._annotation_builder_service.build(
                comparison_result,
            )
            warnings.extend(annotation_plan.warnings)

            rendered_document = self._rendering_service.render(
                request.revised_pdf,
                revised_extracted,
                annotation_plan,
            )
            warnings.extend(rendered_document.warnings)

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
        return self._parsing_service.parse(normalized)

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

    def _unique(self, warnings: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        unique_warnings: list[str] = []

        for warning in warnings:
            if warning in seen:
                continue

            seen.add(warning)
            unique_warnings.append(warning)

        return tuple(unique_warnings)
