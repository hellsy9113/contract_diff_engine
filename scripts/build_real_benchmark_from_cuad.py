from __future__ import annotations

import argparse
import hashlib
import json
from itertools import cycle
from pathlib import Path

from real_benchmark_helpers import (
    MutationResult,
    build_case_document,
    extract_candidate_paragraphs,
    make_pdf_from_text,
    mutate_paragraph,
    write_expected_json,
    write_json,
)

RAW_TEXT_DIR = Path("datasets/raw/cuad/texts")
CUAD_V1_TEXT_DIR = Path("datasets/raw/cuad/CUAD_v1/full_contract_txt")
RAW_METADATA_PATH = Path("datasets/raw/cuad/metadata.jsonl")
BENCHMARK_ROOT = Path("datasets/real_benchmark_v1/cuad")
DEFAULT_CASE_COUNT = 50
MUTATION_TYPES = (
    "amount changed",
    "date changed",
    "number changed",
    "party name changed",
    "jurisdiction changed",
    "sentence added",
    "sentence deleted",
    "phrase modified",
    "termination period changed",
    "liability cap changed",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build real-data benchmark PDF pairs from ingested CUAD text."
    )
    parser.add_argument(
        "--case-count",
        type=int,
        default=DEFAULT_CASE_COUNT,
        help="Number of benchmark cases to create.",
    )
    parser.add_argument(
        "--raw-text-dir",
        type=Path,
        default=RAW_TEXT_DIR,
        help="Folder containing ingested CUAD .txt files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BENCHMARK_ROOT,
        help="Folder where benchmark cases will be written.",
    )
    args = parser.parse_args()

    candidates = _load_candidates(args.raw_text_dir)

    if not candidates and args.raw_text_dir == RAW_TEXT_DIR:
        candidates = _load_candidates(CUAD_V1_TEXT_DIR)

    if not candidates:
        print(
            "No usable CUAD text paragraphs found. Run "
            "`uv run python scripts/ingest_cuad.py` or provide local CUAD text "
            "files under datasets/raw/cuad/texts/. CUAD v1 extracted text is "
            "also supported at datasets/raw/cuad/CUAD_v1/full_contract_txt/."
        )
        return 1

    source_metadata = _load_raw_metadata()
    built_count = build_cases(
        candidates=candidates,
        source_metadata=source_metadata,
        output_dir=args.output_dir,
        case_count=args.case_count,
    )

    print(f"benchmark cases created: {built_count}")
    print(f"benchmark folder: {args.output_dir}")

    if built_count < args.case_count:
        print(
            f"WARNING: requested {args.case_count} cases but only built "
            f"{built_count}. Add more CUAD source text for broader coverage."
        )
        return 1

    return 0


def build_cases(
    candidates: list[dict[str, object]],
    source_metadata: dict[str, dict[str, object]],
    output_dir: Path,
    case_count: int,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    mutation_cycle = cycle(MUTATION_TYPES)
    built = 0
    attempts = 0
    max_attempts = max(case_count * 20, len(candidates) * len(MUTATION_TYPES))

    while built < case_count and attempts < max_attempts:
        candidate = candidates[attempts % len(candidates)]
        mutation_type = next(mutation_cycle)
        paragraph = str(candidate["paragraph"])
        mutation = mutate_paragraph(paragraph, mutation_type)
        attempts += 1

        if mutation is None:
            continue

        case_id = f"case_{built + 1:04d}"
        case_dir = output_dir / case_id
        write_case(
            case_dir=case_dir,
            case_id=case_id,
            mutation=mutation,
            candidate=candidate,
            source_metadata=source_metadata,
        )
        built += 1

    return built


def write_case(
    case_dir: Path,
    case_id: str,
    mutation: MutationResult,
    candidate: dict[str, object],
    source_metadata: dict[str, dict[str, object]],
) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    original_document = build_case_document(mutation.original_text)
    revised_document = build_case_document(mutation.revised_text)
    original_pdf = case_dir / "original.pdf"
    revised_pdf = case_dir / "revised.pdf"
    make_pdf_from_text(original_document, original_pdf)
    make_pdf_from_text(revised_document, revised_pdf)
    write_expected_json(
        output_path=case_dir / "expected.json",
        case_id=case_id,
        source_dataset="CUAD",
        description=mutation.description,
        expected_changes=[mutation.expected_change],
    )
    source_path = str(candidate["source_path"])
    metadata = {
        "case_id": case_id,
        "source_dataset": "CUAD",
        "source_text_path": source_path,
        "source_paragraph_index": candidate["paragraph_index"],
        "source_paragraph_sha256": _sha256(str(candidate["paragraph"])),
        "mutation_type": mutation.mutation_type,
        "original_pdf": str(original_pdf),
        "revised_pdf": str(revised_pdf),
        "source_metadata": source_metadata.get(source_path, {}),
    }
    write_json(case_dir / "metadata.json", metadata)


def _load_candidates(raw_text_dir: Path) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []

    if not raw_text_dir.exists():
        return candidates

    for text_path in sorted(raw_text_dir.glob("*.txt")):
        text = text_path.read_text(encoding="utf-8", errors="ignore")
        paragraphs = extract_candidate_paragraphs(text)

        for paragraph_index, paragraph in enumerate(paragraphs):
            candidates.append(
                {
                    "source_path": str(text_path),
                    "paragraph_index": paragraph_index,
                    "paragraph": paragraph,
                }
            )

    return candidates


def _load_raw_metadata() -> dict[str, dict[str, object]]:
    metadata: dict[str, dict[str, object]] = {}

    if not RAW_METADATA_PATH.exists():
        return metadata

    with RAW_METADATA_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            record = json.loads(line)
            text_path = _metadata_text_path(record)

            if text_path is not None:
                metadata[text_path] = record

    return metadata


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _metadata_text_path(record: object) -> str | None:
    if not isinstance(record, dict):
        return None

    if record.get("file_type") != "txt":
        return None

    for key in ("normalized_path", "normalized_text_path", "text_path"):
        value = record.get(key)

        if isinstance(value, str):
            return value

    return None


if __name__ == "__main__":
    raise SystemExit(main())
