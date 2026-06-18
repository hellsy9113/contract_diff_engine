from __future__ import annotations

import argparse
import json
from pathlib import Path

from contract_diff.extraction.structured.models import PdfIntakeReport
from contract_diff.extraction.structured.pdf_profiler import profile_pdf
from contract_diff.extraction.structured.pipeline import extract_and_process_pdf


def profile_pdf_file(path: Path) -> PdfIntakeReport:
    return profile_pdf(path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile PDF intake quality.")
    parser.add_argument("pdf_path", type=Path, help="PDF file to profile.")
    parser.add_argument(
        "--processed",
        action="store_true",
        help="Also run structured processing and include processor warnings.",
    )
    args = parser.parse_args()

    report = profile_pdf_file(args.pdf_path)
    payload = report.model_dump(mode="json")

    if args.processed and report.is_valid_pdf and not report.is_encrypted:
        try:
            processed = extract_and_process_pdf(args.pdf_path.read_bytes())
            payload["processor_warnings"] = processed.warnings
        except Exception as exc:
            payload["processor_warnings"] = [f"Structured processing failed: {exc}"]

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if report.is_valid_pdf else 1


if __name__ == "__main__":
    raise SystemExit(main())
