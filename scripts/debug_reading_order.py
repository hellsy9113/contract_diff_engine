from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from contract_diff.extraction.structured.pipeline import (
    extract_and_process_pdf,
    get_document_comparison_blocks,
)
from contract_diff.extraction.structured.structured_pdf_reader import (
    extract_structured_pdf,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Debug structured PDF reading order and filtering."
    )
    parser.add_argument("pdf_path", type=Path, help="PDF file to inspect.")
    args = parser.parse_args()

    pdf_bytes = args.pdf_path.read_bytes()
    raw_document = extract_structured_pdf(pdf_bytes)
    processed_document = extract_and_process_pdf(pdf_bytes)
    raw_blocks = [block for page in raw_document.pages for block in page.blocks]
    processed_blocks = [
        block for page in processed_document.pages for block in page.blocks
    ]
    comparison_blocks = get_document_comparison_blocks(processed_document)
    header_blocks = [
        block for block in processed_blocks if block.block_type == "header"
    ]
    footer_blocks = [
        block for block in processed_blocks if block.block_type == "footer"
    ]

    print(f"page count: {processed_document.page_count}")
    print(f"blocks before filtering: {len(raw_blocks)}")
    print(f"comparison blocks after filtering: {len(comparison_blocks)}")
    print(f"detected headers: {len(header_blocks)}")
    print(f"detected footers: {len(footer_blocks)}")

    for page in processed_document.pages:
        counts = Counter(
            block.column_index
            for block in page.blocks
            if block.column_index is not None
        )
        column_summary = dict(sorted(counts.items()))
        print(f"page {page.page_index} detected columns: {column_summary}")

    print("first 10 comparison blocks:")

    for block in comparison_blocks[:10]:
        preview = " ".join(block.text.split())[:100]
        section_path = " > ".join(block.section_path)
        print(
            "  "
            f"page={block.page_index} "
            f"block={block.block_index} "
            f"type={block.block_type} "
            f"column={block.column_index} "
            f"section={section_path!r} "
            f"text={preview!r}"
        )

    if processed_document.warnings:
        print("warnings:")

        for warning in processed_document.warnings:
            print(f"  {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
