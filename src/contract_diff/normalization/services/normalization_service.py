from __future__ import annotations

from contract_diff.models.document.block import Block
from contract_diff.models.document.extracted_document import ExtractedDocument
from contract_diff.normalization.models.normalized_document import NormalizedDocument
from contract_diff.normalization.models.normalized_page import NormalizedPage
from contract_diff.normalization.models.normalized_text_unit import (
    NormalizedTextUnit,
)
from contract_diff.normalization.utils.text_normalizer import TextNormalizer


class NormalizationService:
    """
    Converts extracted document structure into traceable normalized text.
    """

    def normalize(self, document: ExtractedDocument) -> NormalizedDocument:
        unit_index = 1
        normalized_pages: list[NormalizedPage] = []

        for page in document.pages:
            units: list[NormalizedTextUnit] = []

            for block in page.blocks:
                normalized_text = TextNormalizer.normalize(block.text)

                if not normalized_text:
                    continue

                units.append(
                    NormalizedTextUnit(
                        id=f"normalized-unit-{unit_index}",
                        text=normalized_text,
                        page_number=page.page_number,
                        source_page_id=page.id,
                        source_block_id=block.id,
                        source_line_ids=self._line_ids(block),
                        source_span_ids=self._span_ids(block),
                    )
                )
                unit_index += 1

            normalized_pages.append(
                NormalizedPage(
                    id=f"normalized-page-{page.page_number}",
                    page_number=page.page_number,
                    source_page_id=page.id,
                    units=tuple(units),
                )
            )

        return NormalizedDocument(
            format=document.format,
            metadata=document.metadata,
            pages=tuple(normalized_pages),
        )

    def _line_ids(self, block: Block) -> tuple[str, ...]:
        return tuple(line.id for line in block.lines)

    def _span_ids(self, block: Block) -> tuple[str, ...]:
        return tuple(
            span.id
            for line in block.lines
            for span in line.spans
        )
