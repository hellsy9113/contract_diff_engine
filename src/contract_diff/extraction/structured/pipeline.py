from __future__ import annotations

from contract_diff.extraction.structured.block_classifier import classify_blocks
from contract_diff.extraction.structured.columns import apply_column_detection
from contract_diff.extraction.structured.models import StructuredDocument, TextBlock
from contract_diff.extraction.structured.pdf_profiler import profile_pdf
from contract_diff.extraction.structured.reading_order import (
    get_comparison_blocks,
    resolve_reading_order,
)
from contract_diff.extraction.structured.sections import assign_section_paths
from contract_diff.extraction.structured.structured_pdf_reader import (
    extract_structured_pdf,
)


def extract_and_process_pdf(pdf_bytes: bytes) -> StructuredDocument:
    profile = profile_pdf(pdf_bytes)
    document = extract_structured_pdf(pdf_bytes)
    processed_document = process_structured_document(document)
    warnings = [*profile.warnings, *processed_document.warnings]
    return processed_document.model_copy(update={"warnings": _dedupe(warnings)})


def process_structured_document(document: StructuredDocument) -> StructuredDocument:
    ordered_document = resolve_reading_order(document)
    column_document = apply_column_detection(ordered_document)
    classified_document = classify_blocks(column_document)
    sectioned_document = assign_section_paths(classified_document)
    return sectioned_document


def get_document_comparison_blocks(
    document: StructuredDocument,
) -> list[TextBlock]:
    return get_comparison_blocks(document)


def get_document_comparison_text(document: StructuredDocument) -> str:
    return "\n\n".join(
        block.text for block in get_document_comparison_blocks(document)
    ).strip()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []

    for value in values:
        if value in seen:
            continue

        seen.add(value)
        deduped.append(value)

    return deduped
