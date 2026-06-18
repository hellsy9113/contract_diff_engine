from __future__ import annotations

import re

from contract_diff.extraction.structured.models import (
    ExtractedPage,
    StructuredDocument,
    TextBlock,
)
from contract_diff.extraction.structured.reading_order import get_comparison_blocks

NUMBERED_HEADING_PATTERN = re.compile(
    r"^(?:section\s+)?(?P<number>\d+(?:\.\d+)*)(?:\.|\s)\s*(?P<title>.*)$",
    re.IGNORECASE,
)
TOP_LEVEL_HEADING_PATTERN = re.compile(
    r"^(article\s+[IVXLCDM]+|exhibit\s+[A-Z0-9]+|schedule\s+[A-Z0-9]+)",
    re.IGNORECASE,
)


def assign_section_paths(document: StructuredDocument) -> StructuredDocument:
    section_path_by_key: dict[tuple[int, int], list[str]] = {}
    section_stack: list[str] = []

    for block in get_comparison_blocks(document):
        if block.block_type == "heading":
            level = _heading_level(block.text)
            section_stack = _updated_stack(section_stack, block.text, level)
            section_path_by_key[(block.page_index, block.block_index)] = list(
                section_stack
            )
            continue

        section_path_by_key[(block.page_index, block.block_index)] = list(
            section_stack
        )

    pages: list[ExtractedPage] = []

    for page in document.pages:
        blocks: list[TextBlock] = []

        for block in page.blocks:
            key = (block.page_index, block.block_index)
            blocks.append(
                block.model_copy(
                    update={
                        "section_path": section_path_by_key.get(
                            key,
                            block.section_path,
                        )
                    }
                )
            )

        pages.append(page.model_copy(update={"blocks": blocks}))

    return document.model_copy(update={"pages": pages})


def _heading_level(text: str) -> int:
    normalized = " ".join(text.split()).strip()
    number_match = NUMBERED_HEADING_PATTERN.match(normalized)

    if number_match is not None:
        number = number_match.group("number")
        return number.count(".") + 1

    if TOP_LEVEL_HEADING_PATTERN.match(normalized):
        return 1

    return 1


def _updated_stack(
    section_stack: list[str],
    heading_text: str,
    level: int,
) -> list[str]:
    normalized_heading = " ".join(heading_text.split()).strip()
    retained = section_stack[: max(0, level - 1)]
    retained.append(normalized_heading)
    return retained
