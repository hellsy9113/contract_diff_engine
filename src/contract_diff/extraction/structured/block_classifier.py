from __future__ import annotations

import re

from contract_diff.extraction.structured.header_footer import is_page_number_text
from contract_diff.extraction.structured.models import (
    ExtractedPage,
    StructuredDocument,
    TextBlock,
)

HEADING_PATTERNS = (
    re.compile(r"^\d+(?:\.\d+)*\.?\s+[A-Z][\w ,/&()-]{2,}$"),
    re.compile(r"^section\s+\d+(?:\.\d+)*\s+.+$", re.IGNORECASE),
    re.compile(r"^article\s+[IVXLCDM]+(?:\s+.+)?$", re.IGNORECASE),
    re.compile(r"^exhibit\s+[A-Z0-9]+(?:\s+.+)?$", re.IGNORECASE),
    re.compile(r"^schedule\s+[A-Z0-9]+(?:\s+.+)?$", re.IGNORECASE),
)
LIST_ITEM_PATTERNS = (
    re.compile(r"^[\u2022*-]\s+.+"),
    re.compile(r"^\([a-z]\)\s+.+", re.IGNORECASE),
    re.compile(r"^\((?:i|ii|iii|iv|v|vi|vii|viii|ix|x)\)\s+.+", re.IGNORECASE),
    re.compile(r"^\d+[.)]\s+.+"),
)
ALL_CAPS_MIN_ALPHA = 6
SHORT_HEADING_MAX_CHARS = 90
PARAGRAPH_MIN_CHARS = 35


def classify_blocks(document: StructuredDocument) -> StructuredDocument:
    pages: list[ExtractedPage] = []

    for page in document.pages:
        blocks = [
            block.model_copy(update={"block_type": classify_block(block)})
            for block in page.blocks
        ]
        pages.append(page.model_copy(update={"blocks": blocks}))

    return document.model_copy(update={"pages": pages})


def classify_block(block: TextBlock) -> str:
    if block.block_type in {"header", "footer"}:
        return block.block_type

    text = " ".join(block.text.split())

    if _is_noise(text):
        return "noise"

    if _is_heading(text):
        return "heading"

    if _is_list_item(text):
        return "list_item"

    if _is_table_candidate(block):
        return "table_candidate"

    if len(text) >= PARAGRAPH_MIN_CHARS:
        return "paragraph"

    return "unknown"


def _is_noise(text: str) -> bool:
    if not text:
        return True

    if is_page_number_text(text):
        return True

    alpha_count = sum(1 for char in text if char.isalpha())

    if alpha_count == 0:
        return True

    return len(text) <= 2


def _is_heading(text: str) -> bool:
    if any(pattern.match(text) for pattern in HEADING_PATTERNS):
        return True

    alpha_chars = [char for char in text if char.isalpha()]

    if len(alpha_chars) < ALL_CAPS_MIN_ALPHA:
        return False

    return (
        len(text) <= SHORT_HEADING_MAX_CHARS
        and text.upper() == text
        and len(text.split()) <= 10
    )


def _is_list_item(text: str) -> bool:
    return any(pattern.match(text) for pattern in LIST_ITEM_PATTERNS)


def _is_table_candidate(block: TextBlock) -> bool:
    if "|" in block.text and block.text.count("|") >= 2:
        return True

    lines = [line.text.strip() for line in block.lines if line.text.strip()]

    if len(lines) < 2:
        return bool(re.search(r"\S+\s{3,}\S+\s{3,}\S+", block.text))

    short_lines = sum(1 for line in lines if len(line) <= 35)
    fragmented_ratio = short_lines / len(lines)
    return fragmented_ratio >= 0.7 and len(lines) >= 3
