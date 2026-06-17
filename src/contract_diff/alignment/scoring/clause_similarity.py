from __future__ import annotations

from contract_diff.alignment.models.alignment_score import AlignmentScore
from contract_diff.alignment.scoring.heading_similarity import HeadingSimilarity
from contract_diff.alignment.scoring.number_similarity import NumberSimilarity
from contract_diff.alignment.scoring.position_similarity import PositionSimilarity
from contract_diff.alignment.scoring.section_similarity import SectionSimilarity
from contract_diff.alignment.scoring.text_similarity import TextSimilarity
from contract_diff.parsing.models.clause import Clause
from contract_diff.parsing.models.structured_document import StructuredDocument


class ClauseSimilarityScorer:
    """
    Deterministic clause alignment scoring.
    """

    @classmethod
    def score(
        cls,
        original_clause: Clause,
        revised_clause: Clause,
        original_document: StructuredDocument,
        revised_document: StructuredDocument,
        original_index: int,
        revised_index: int,
    ) -> AlignmentScore:
        original_section = cls._section_title(
            original_document,
            original_clause.section_id,
        )
        revised_section = cls._section_title(
            revised_document,
            revised_clause.section_id,
        )

        clause_number_score = NumberSimilarity.score(
            original_clause.number,
            revised_clause.number,
        )
        text_score = TextSimilarity.score(original_clause.text, revised_clause.text)
        section_score = SectionSimilarity.score(original_section, revised_section)
        heading_score = HeadingSimilarity.score(
            original_clause.title,
            revised_clause.title,
        )
        position_score = PositionSimilarity.score(
            original_index,
            revised_index,
            len(original_document.clauses),
            len(revised_document.clauses),
        )
        overall = round(
            (clause_number_score * 0.30)
            + (text_score * 0.25)
            + (section_score * 0.20)
            + (heading_score * 0.15)
            + (position_score * 0.10),
            2,
        )

        return AlignmentScore(
            overall=overall,
            clause_number_score=clause_number_score,
            heading_score=heading_score,
            section_score=section_score,
            text_score=text_score,
            position_score=position_score,
        )

    @classmethod
    def _section_title(
        cls,
        document: StructuredDocument,
        section_id: str | None,
    ) -> str | None:
        if section_id is None:
            return None

        for section in document.sections:
            if section.id == section_id:
                return section.title

        return None
