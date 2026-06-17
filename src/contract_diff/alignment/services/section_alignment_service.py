from __future__ import annotations

from contract_diff.alignment.scoring.text_similarity import TextSimilarity
from contract_diff.parsing.models.structured_document import StructuredDocument


class SectionAlignmentService:
    """
    Deterministically maps original section IDs to revised section IDs.
    """

    def align(
        self,
        original_document: StructuredDocument,
        revised_document: StructuredDocument,
    ) -> dict[str, str]:
        section_map: dict[str, str] = {}
        used_revised_section_ids: set[str] = set()

        for original_section in original_document.sections:
            candidates = [
                (
                    TextSimilarity.score(original_section.title, revised_section.title),
                    revised_section.id,
                )
                for revised_section in revised_document.sections
                if revised_section.id not in used_revised_section_ids
            ]

            if not candidates:
                continue

            score, revised_section_id = max(candidates, key=lambda item: item[0])

            if score >= 60.0:
                section_map[original_section.id] = revised_section_id
                used_revised_section_ids.add(revised_section_id)

        return section_map
