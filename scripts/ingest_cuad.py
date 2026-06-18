from __future__ import annotations

import argparse
import importlib
import json
import shutil
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, cast

import fitz
from real_benchmark_helpers import make_pdf_from_text

RAW_ROOT = Path("datasets/raw/cuad")
PDF_DIR = RAW_ROOT / "pdfs"
TEXT_DIR = RAW_ROOT / "texts"
METADATA_PATH = RAW_ROOT / "metadata.jsonl"
HF_DATASET_CANDIDATES = (
    "theatticusproject/cuad",
    "cuad",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest CUAD contracts into local raw benchmark storage."
    )
    parser.add_argument(
        "--local-cuad-dir",
        type=Path,
        default=None,
        help="Local CUAD folder containing .txt and/or .pdf files.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of contracts to ingest.",
    )
    args = parser.parse_args()

    _ensure_dirs()
    records: list[dict[str, object]]

    if args.local_cuad_dir is not None:
        records = ingest_local_cuad(args.local_cuad_dir, args.limit)
    else:
        hf_records = ingest_huggingface_cuad(args.limit)

        if hf_records is None:
            print(
                "CUAD Hugging Face loading is unavailable. Install the optional "
                "`datasets` package or rerun with --local-cuad-dir PATH."
            )
            return 1

        records = hf_records

    _write_metadata(records)
    print(f"ingested contracts: {len(records)}")
    print(f"raw CUAD folder: {RAW_ROOT}")
    return 0


def ingest_huggingface_cuad(limit: int | None) -> list[dict[str, object]] | None:
    try:
        datasets_module = importlib.import_module("datasets")
    except ModuleNotFoundError:
        return None

    load_dataset = getattr(datasets_module, "load_dataset", None)

    if load_dataset is None:
        return None

    last_error: Exception | None = None

    for dataset_name in HF_DATASET_CANDIDATES:
        try:
            dataset = load_dataset(dataset_name)
            return _ingest_hf_dataset(dataset, dataset_name, limit)
        except Exception as exc:
            last_error = exc

    print(f"Could not load CUAD from Hugging Face: {last_error}")
    return None


def ingest_local_cuad(
    local_dir: Path,
    limit: int | None,
) -> list[dict[str, object]]:
    if not local_dir.exists():
        raise FileNotFoundError(f"Local CUAD folder does not exist: {local_dir}")

    records: list[dict[str, object]] = []
    seen_stems: set[str] = set()
    files = sorted(
        path
        for path in local_dir.rglob("*")
        if path.suffix.casefold() in {".txt", ".pdf"}
    )

    for path in files:
        if limit is not None and len(records) >= limit:
            break

        stem = _safe_stem(path.stem)

        if stem in seen_stems:
            continue

        seen_stems.add(stem)
        text = _text_for_local_file(path)

        if not text.strip():
            continue

        text_path = TEXT_DIR / f"{stem}.txt"
        pdf_path = PDF_DIR / f"{stem}.pdf"
        text_path.write_text(text, encoding="utf-8")

        pdf_generated = True

        if path.suffix.casefold() == ".pdf":
            shutil.copyfile(path, pdf_path)
            pdf_generated = False
        else:
            source_pdf = path.with_suffix(".pdf")

            if source_pdf.exists():
                shutil.copyfile(source_pdf, pdf_path)
                pdf_generated = False
            else:
                make_pdf_from_text(text, pdf_path)

        records.append(
            {
                "source_dataset": "CUAD",
                "source": "local",
                "source_path": str(path),
                "source_id": stem,
                "text_path": str(text_path),
                "pdf_path": str(pdf_path),
                "pdf_generated_from_text": pdf_generated,
            }
        )

    return records


def _ingest_hf_dataset(
    dataset: Any,
    dataset_name: str,
    limit: int | None,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    for split_name, split in _iter_splits(dataset):
        for index, row in enumerate(split):
            if limit is not None and len(records) >= limit:
                return records

            text = _row_text(row)

            if not text:
                continue

            source_id = _safe_stem(
                str(_row_value(row, ("title", "file_name", "id")) or "")
                or f"{split_name}_{index:05d}"
            )
            text_path = TEXT_DIR / f"{source_id}.txt"
            pdf_path = PDF_DIR / f"{source_id}.pdf"
            text_path.write_text(text, encoding="utf-8")
            pdf_generated = not _write_row_pdf(row, pdf_path)

            if pdf_generated:
                make_pdf_from_text(text, pdf_path)

            records.append(
                {
                    "source_dataset": "CUAD",
                    "source": "huggingface",
                    "huggingface_dataset": dataset_name,
                    "split": split_name,
                    "source_id": source_id,
                    "text_path": str(text_path),
                    "pdf_path": str(pdf_path),
                    "pdf_generated_from_text": pdf_generated,
                }
            )

    return records


def _iter_splits(dataset: Any) -> Iterable[tuple[str, Iterable[Mapping[str, Any]]]]:
    if hasattr(dataset, "items"):
        for split_name, split in dataset.items():
            yield str(split_name), split
        return

    yield "default", dataset


def _row_text(row: Mapping[str, Any]) -> str:
    value = _row_value(
        row,
        (
            "text",
            "contract_text",
            "context",
            "document_text",
            "raw_text",
        ),
    )

    if isinstance(value, str):
        return value

    return ""


def _row_value(row: Mapping[str, Any], keys: tuple[str, ...]) -> object | None:
    for key in keys:
        value = row.get(key)

        if value:
            return cast(object, value)

    return None


def _write_row_pdf(row: Mapping[str, Any], pdf_path: Path) -> bool:
    pdf_value = _row_value(row, ("pdf", "pdf_bytes", "document_pdf", "file"))

    if isinstance(pdf_value, bytes):
        pdf_path.write_bytes(pdf_value)
        return True

    if isinstance(pdf_value, dict):
        bytes_value = pdf_value.get("bytes")
        path_value = pdf_value.get("path")

        if isinstance(bytes_value, bytes):
            pdf_path.write_bytes(bytes_value)
            return True

        if isinstance(path_value, str) and Path(path_value).exists():
            shutil.copyfile(path_value, pdf_path)
            return True

    if isinstance(pdf_value, str) and Path(pdf_value).exists():
        shutil.copyfile(pdf_value, pdf_path)
        return True

    return False


def _text_for_local_file(path: Path) -> str:
    if path.suffix.casefold() == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    return _extract_pdf_text(path)


def _extract_pdf_text(path: Path) -> str:
    with fitz.open(path) as document:
        return "\n".join(page.get_text() for page in document)


def _safe_stem(value: str) -> str:
    cleaned = "".join(
        char if char.isalnum() else "-"
        for char in value.strip().casefold()
    )
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return cleaned[:96] or "cuad-contract"


def _ensure_dirs() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)


def _write_metadata(records: list[dict[str, object]]) -> None:
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METADATA_PATH.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, sort_keys=True))
            file.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
