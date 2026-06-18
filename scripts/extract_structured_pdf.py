from __future__ import annotations

import argparse
from pathlib import Path

from contract_diff.extraction.structured.pipeline import extract_and_process_pdf
from contract_diff.extraction.structured.structured_pdf_reader import (
    extract_structured_pdf,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect structured PDF extraction.")
    parser.add_argument("pdf_path", type=Path, help="PDF file to extract.")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Show raw structured extraction before processing heuristics.",
    )
    args = parser.parse_args()

    pdf_bytes = args.pdf_path.read_bytes()
    document = (
        extract_structured_pdf(pdf_bytes)
        if args.raw
        else extract_and_process_pdf(pdf_bytes)
    )
    blocks = [block for page in document.pages for block in page.blocks]
    words = [word for page in document.pages for word in page.words]

    print(f"page count: {document.page_count}")
    print(f"total blocks: {len(blocks)}")
    print(f"total words: {len(words)}")
    print("first 5 blocks:")

    for block in blocks[:5]:
        preview = " ".join(block.text.split())[:120]
        bbox = block.bbox
        print(
            "  "
            f"page={block.page_index} "
            f"block={block.block_index} "
            f"type={block.block_type} "
            f"column={block.column_index} "
            f"bbox=({bbox.x0:.1f}, {bbox.y0:.1f}, {bbox.x1:.1f}, {bbox.y1:.1f}) "
            f"text={preview!r}"
        )

    if document.warnings:
        print("warnings:")

        for warning in document.warnings:
            print(f"  {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
