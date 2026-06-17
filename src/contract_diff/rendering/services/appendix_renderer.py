from typing import Any

from contract_diff.annotation.models.annotation_appendix_entry import (
    AnnotationAppendixEntry,
)
from contract_diff.annotation.models.annotation_plan import AnnotationPlan
from contract_diff.rendering.styles.pdf_colors import BLACK


class AppendixRenderer:
    """
    Appends metadata pages describing rendered annotations.
    """

    def render(self, pdf_document: Any, annotation_plan: AnnotationPlan) -> None:
        for entry in annotation_plan.appendix_entries:
            page = pdf_document.new_page(width=595, height=842)
            page.insert_textbox(
                page.rect + (72, 72, -72, -72),
                self._entry_text(entry),
                fontsize=10,
                fontname="helv",
                color=BLACK,
            )

    def _entry_text(self, entry: AnnotationAppendixEntry) -> str:
        lines = [
            f"Annotation {entry.annotation_id}",
            f"Type: {entry.annotation_type.value.title()}",
            "Page: "
            f"{entry.page_number if entry.page_number is not None else 'Unknown'}",
            f"Heading: {entry.heading or 'Unknown'}",
            "",
            "Original:",
            entry.original_text or "Not present in original document",
            "",
            "Revised:",
            entry.revised_text or "Not present in revised document",
        ]

        if entry.notes:
            lines.extend(("", "Notes:", *entry.notes))

        return "\n".join(lines)
