from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

RAW_ROOT = Path("datasets/raw/cuad")
CUAD_V1_ROOT = RAW_ROOT / "CUAD_v1"
TEXT_DIR = RAW_ROOT / "texts"
PDF_DIR = RAW_ROOT / "pdfs"
METADATA_PATH = RAW_ROOT / "metadata.jsonl"

UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
REPEATED_UNDERSCORES = re.compile(r"_+")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize a local extracted CUAD_v1 folder into raw text/pdf folders."
        )
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=CUAD_V1_ROOT,
        help="Local extracted CUAD_v1 folder to normalize.",
    )
    parser.add_argument(
        "--text-dir",
        type=Path,
        default=TEXT_DIR,
        help="Destination folder for normalized TXT files.",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=PDF_DIR,
        help="Destination folder for normalized PDF files.",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=METADATA_PATH,
        help="Destination metadata.jsonl path.",
    )
    args = parser.parse_args()

    if not args.source_dir.exists():
        print(f"CUAD source folder not found: {args.source_dir}")
        return 1

    args.text_dir.mkdir(parents=True, exist_ok=True)
    args.pdf_dir.mkdir(parents=True, exist_ok=True)
    args.metadata_path.parent.mkdir(parents=True, exist_ok=True)

    txt_files = find_files_by_extension(args.source_dir, ".txt")
    pdf_files = find_files_by_extension(args.source_dir, ".pdf")

    print(f"CUAD source folder: {args.source_dir}")
    print(f"TXT files found: {len(txt_files)}")
    print(f"PDF files found: {len(pdf_files)}")

    records: list[dict[str, object]] = []
    copied_txt = copy_txt_files(
        txt_files=txt_files,
        text_dir=args.text_dir,
        records=records,
    )
    copied_pdf = copy_pdf_files(
        pdf_files=pdf_files,
        pdf_dir=args.pdf_dir,
        records=records,
    )
    write_metadata(args.metadata_path, records)

    print(f"TXT files copied: {len(copied_txt)}")
    print(f"PDF files copied: {len(copied_pdf)}")
    print(f"metadata path: {args.metadata_path}")
    print("top 5 copied TXT files:")
    print_top_files(copied_txt)
    print("top 5 copied PDF files:")
    print_top_files(copied_pdf)

    return 0


def find_files_by_extension(root: Path, extension: str) -> list[Path]:
    expected_extension = extension.casefold()
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.casefold() == expected_extension
    )


def copy_txt_files(
    txt_files: list[Path],
    text_dir: Path,
    records: list[dict[str, object]],
) -> list[Path]:
    copied: list[Path] = []
    used_names: set[str] = set()

    for source_path in txt_files:
        target_name = unique_safe_filename(source_path.name, used_names)
        target_path = text_dir / target_name
        shutil.copy2(source_path, target_path)
        text_chars = len(target_path.read_text(encoding="utf-8", errors="ignore"))
        records.append(
            {
                "index": len(records),
                "source_dataset": "CUAD",
                "file_type": "txt",
                "source_path": str(source_path),
                "normalized_path": str(target_path),
                "file_name": target_name,
                "text_chars": text_chars,
            }
        )
        copied.append(target_path)

    return copied


def copy_pdf_files(
    pdf_files: list[Path],
    pdf_dir: Path,
    records: list[dict[str, object]],
) -> list[Path]:
    copied: list[Path] = []
    used_names: set[str] = set()

    for source_path in pdf_files:
        target_name = unique_safe_filename(source_path.name, used_names)
        target_path = pdf_dir / target_name
        shutil.copy2(source_path, target_path)
        records.append(
            {
                "index": len(records),
                "source_dataset": "CUAD",
                "file_type": "pdf",
                "source_path": str(source_path),
                "normalized_path": str(target_path),
                "file_name": target_name,
                "file_size_bytes": target_path.stat().st_size,
            }
        )
        copied.append(target_path)

    return copied


def unique_safe_filename(filename: str, used_names: set[str]) -> str:
    safe_name = safe_filename(filename)

    if safe_name not in used_names:
        used_names.add(safe_name)
        return safe_name

    suffix = Path(safe_name).suffix
    stem = safe_name[: -len(suffix)] if suffix else safe_name
    index = 1

    while True:
        candidate = f"{index:04d}_{stem}{suffix}"

        if candidate not in used_names:
            used_names.add(candidate)
            return candidate

        index += 1


def safe_filename(filename: str) -> str:
    path = Path(filename)
    stem = UNSAFE_FILENAME_CHARS.sub("_", path.stem.strip())
    stem = REPEATED_UNDERSCORES.sub("_", stem).strip("._-")
    extension = UNSAFE_FILENAME_CHARS.sub("_", path.suffix.strip()).casefold()
    extension = REPEATED_UNDERSCORES.sub("_", extension)

    if not stem:
        stem = "cuad_file"

    if extension and not extension.startswith("."):
        extension = f".{extension}"

    return f"{stem}{extension}"


def write_metadata(metadata_path: Path, records: list[dict[str, object]]) -> None:
    with metadata_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, sort_keys=True))
            file.write("\n")


def print_top_files(paths: list[Path]) -> None:
    for path in paths[:5]:
        print(f"  {path}")

    if not paths:
        print("  none")


if __name__ == "__main__":
    raise SystemExit(main())
