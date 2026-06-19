from __future__ import annotations

import argparse
import os
from collections import Counter
from pathlib import Path

import fitz
from real_benchmark_helpers import load_json, write_json

from contract_diff.rendering.diagnostics import analyze_rendered_pdf
from contract_diff.services.compare_v2 import compare_pdf_bytes_v2

JsonObject = dict[str, object]

BENCHMARK_ROOT = Path("datasets/real_benchmark_v1/cuad")
GLOBAL_REPORT_PATH = BENCHMARK_ROOT / "benchmark_report.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run structured compare v2 against real CUAD benchmark cases."
    )
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=BENCHMARK_ROOT,
        help="Folder containing benchmark case directories.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=GLOBAL_REPORT_PATH,
        help="Path where the global benchmark_report.json will be written.",
    )
    parser.add_argument(
        "--debug-diff",
        action="store_true",
        help="Write diff-debug.json next to each generated output.pdf.",
    )
    args = parser.parse_args()
    case_dirs = _case_dirs(args.benchmark_dir)

    if not case_dirs:
        print(
            "No benchmark cases found. Run "
            "`uv run python scripts/build_real_benchmark_from_cuad.py` first."
        )
        return 1

    debug_diff = args.debug_diff or _truthy_env("DEBUG_DIFF")
    results = [run_case(case_dir, debug_diff=debug_diff) for case_dir in case_dirs]
    global_report = build_global_report(results)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.report_path, global_report)
    print(f"benchmark cases run: {len(results)}")
    print(f"global report written: {args.report_path}")
    return 0


def run_case(case_dir: Path, *, debug_diff: bool = False) -> JsonObject:
    original_pdf = case_dir / "original.pdf"
    revised_pdf = case_dir / "revised.pdf"
    output_pdf = case_dir / "output.pdf"
    case_report_path = case_dir / "report.json"
    metadata = _load_case_metadata(case_dir)
    mutation_type = _mutation_type(metadata)

    try:
        output_bytes, report = compare_pdf_bytes_v2(
            original_pdf.read_bytes(),
            revised_pdf.read_bytes(),
            original_filename=original_pdf.name,
            revised_filename=revised_pdf.name,
            debug=debug_diff,
            debug_output_path=(
                output_pdf.with_name("diff-debug.json") if debug_diff else None
            ),
        )
        output_pdf.write_bytes(output_bytes)
        diagnostics = analyze_rendered_pdf(output_bytes)
        valid_pdf = _is_valid_pdf(output_pdf)
        case_result: JsonObject = {
            "case_id": case_dir.name,
            "status": "passed" if valid_pdf else "failed",
            "mutation_type": mutation_type,
            "output_pdf": str(output_pdf),
            "report_json": str(case_report_path),
            "valid_pdf": valid_pdf,
            "confidence": report.comparison_quality.confidence,
            "change_count": len(report.changes),
            "unwanted_annotation_count": (
                report.comparison_quality.unwanted_annotation_count
            ),
            "dense_highlight_pages": (report.comparison_quality.dense_highlight_pages),
            "diagnostics": diagnostics,
        }
        write_json(
            case_report_path,
            {
                "case": case_result,
                "comparison_report": report.model_dump(mode="json"),
            },
        )
        return case_result

    except Exception as exc:
        case_result = {
            "case_id": case_dir.name,
            "status": "failed",
            "mutation_type": mutation_type,
            "output_pdf": str(output_pdf),
            "report_json": str(case_report_path),
            "valid_pdf": False,
            "confidence": 0.0,
            "change_count": 0,
            "unwanted_annotation_count": 0,
            "dense_highlight_pages": [],
            "error": f"{exc.__class__.__name__}: {exc}",
        }
        write_json(case_report_path, {"case": case_result})
        return case_result


def build_global_report(case_results: list[JsonObject]) -> JsonObject:
    passed = sum(1 for result in case_results if result.get("status") == "passed")
    failed = len(case_results) - passed
    confidence_values = [
        _number_value(result.get("confidence", 0.0)) for result in case_results
    ]
    change_counts = [
        _integer_value(result.get("change_count", 0)) for result in case_results
    ]
    unwanted_annotation_count = sum(
        _integer_value(result.get("unwanted_annotation_count", 0))
        for result in case_results
    )
    dense_highlight_pages = _all_dense_pages(case_results)
    failures_by_mutation_type = Counter(
        str(result.get("mutation_type", "unknown"))
        for result in case_results
        if result.get("status") != "passed"
    )

    return {
        "source_dataset": "CUAD",
        "engine": "compare_v2",
        "total_cases": len(case_results),
        "passed": passed,
        "failed": failed,
        "average_confidence": _average(confidence_values),
        "average_changes_per_case": _average(change_counts),
        "unwanted_annotation_count": unwanted_annotation_count,
        "dense_highlight_pages": dense_highlight_pages,
        "failures_by_mutation_type": dict(sorted(failures_by_mutation_type.items())),
        "cases": case_results,
    }


def _case_dirs(benchmark_dir: Path) -> list[Path]:
    if not benchmark_dir.exists():
        return []

    return sorted(
        path
        for path in benchmark_dir.iterdir()
        if path.is_dir()
        and (path / "original.pdf").exists()
        and (path / "revised.pdf").exists()
    )


def _load_case_metadata(case_dir: Path) -> object:
    metadata_path = case_dir / "metadata.json"

    if not metadata_path.exists():
        return {}

    return load_json(metadata_path)


def _mutation_type(metadata: object) -> str:
    if not isinstance(metadata, dict):
        return "unknown"

    value = metadata.get("mutation_type", "unknown")
    return value if isinstance(value, str) else "unknown"


def _is_valid_pdf(pdf_path: Path) -> bool:
    try:
        with fitz.open(pdf_path) as document:
            return int(document.page_count) > 0
    except Exception:
        return False


def _all_dense_pages(case_results: list[JsonObject]) -> list[dict[str, object]]:
    dense_pages: list[dict[str, object]] = []

    for result in case_results:
        pages = result.get("dense_highlight_pages", [])

        if not isinstance(pages, list):
            continue

        for page in pages:
            if not isinstance(page, int):
                continue

            dense_pages.append(
                {
                    "case_id": str(result.get("case_id", "")),
                    "page": page,
                }
            )

    return dense_pages


def _average(values: list[float] | list[int]) -> float:
    if not values:
        return 0.0

    return round(sum(values) / len(values), 4)


def _number_value(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)

    return 0.0


def _truthy_env(name: str) -> bool:
    value = os.getenv(name)

    if value is None:
        return False

    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _integer_value(value: object) -> int:
    if isinstance(value, int):
        return value

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
