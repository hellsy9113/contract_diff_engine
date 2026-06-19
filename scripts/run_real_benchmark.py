from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import fitz
from real_benchmark_helpers import (
    UNWANTED_ANNOTATION_TYPES,
    count_pdf_annotations,
    load_json,
    write_json,
)

from contract_diff.core.models.engine_status import EngineStatus
from contract_diff.core.services.contract_diff_engine import ContractDiffEngine

JsonObject = dict[str, object]

BENCHMARK_ROOT = Path("datasets/real_benchmark_v1/cuad")
REPORT_PATH = BENCHMARK_ROOT / "report.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the contract diff engine against real CUAD benchmark cases."
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
        default=REPORT_PATH,
        help="Path where report.json will be written.",
    )
    args = parser.parse_args()

    case_dirs = _case_dirs(args.benchmark_dir)

    if not case_dirs:
        print(
            "No benchmark cases found. Run "
            "`uv run python scripts/build_real_benchmark_from_cuad.py` first."
        )
        return 1

    engine = ContractDiffEngine()
    results = [run_case(engine, case_dir) for case_dir in case_dirs]
    report = _report(results)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.report_path, report)
    print(f"benchmark cases run: {len(results)}")
    print(f"report written: {args.report_path}")
    return 0


def run_case(engine: ContractDiffEngine, case_dir: Path) -> JsonObject:
    original_pdf = case_dir / "original.pdf"
    revised_pdf = case_dir / "revised.pdf"
    output_pdf = case_dir / "output.pdf"
    expected_path = case_dir / "expected.json"
    expected = load_json(expected_path)

    if output_pdf.exists():
        output_pdf.unlink()

    result = engine.compare(
        original_pdf.read_bytes(),
        revised_pdf.read_bytes(),
        original_filename=original_pdf.name,
        revised_filename=revised_pdf.name,
    )

    case_result: JsonObject = {
        "case_id": case_dir.name,
        "status": result.status.value,
        "output_pdf": str(output_pdf),
        "warnings": list(result.warnings),
        "checks": {},
    }

    if result.status is not EngineStatus.SUCCESS or result.rendered_document is None:
        case_result["checks"] = {
            "valid_pdf": False,
            "no_unwanted_annotations": False,
            "has_highlight_when_changes_exist": False,
            "contains_expected_revised_text": False,
        }
        case_result["message"] = result.message
        return case_result

    output_pdf.write_bytes(result.rendered_document.data)
    annotation_counts = count_pdf_annotations(output_pdf)
    output_text = _extract_pdf_text(output_pdf)
    checks = {
        "valid_pdf": _is_valid_pdf(output_pdf),
        "no_unwanted_annotations": _has_no_unwanted_annotations(annotation_counts),
        "has_highlight_when_changes_exist": _has_highlight_when_expected(
            annotation_counts,
            expected,
        ),
        "contains_expected_revised_text": _contains_expected_revised_text(
            output_text,
            expected,
        ),
    }
    case_result["checks"] = checks
    case_result["annotation_counts"] = annotation_counts
    return case_result


def _case_dirs(benchmark_dir: Path) -> list[Path]:
    if not benchmark_dir.exists():
        return []

    return sorted(
        path
        for path in benchmark_dir.iterdir()
        if path.is_dir()
        and (path / "original.pdf").exists()
        and (path / "revised.pdf").exists()
        and (path / "expected.json").exists()
    )


def _report(case_results: list[JsonObject]) -> JsonObject:
    check_names = (
        "valid_pdf",
        "no_unwanted_annotations",
        "has_highlight_when_changes_exist",
        "contains_expected_revised_text",
    )
    summary: dict[str, int] = {
        "total_cases": len(case_results),
        "successful_engine_runs": sum(
            1 for result in case_results if result["status"] == "success"
        ),
    }

    for check_name in check_names:
        summary[check_name] = sum(
            1 for result in case_results if _check_passed(result, check_name)
        )

    return {
        "source_dataset": "CUAD",
        "summary": summary,
        "cases": case_results,
    }


def _is_valid_pdf(pdf_path: Path) -> bool:
    try:
        with fitz.open(pdf_path) as document:
            return int(document.page_count) > 0
    except Exception:
        return False


def _check_passed(case_result: JsonObject, check_name: str) -> bool:
    checks = case_result.get("checks")

    if not isinstance(checks, dict):
        return False

    return checks.get(check_name) is True


def _has_no_unwanted_annotations(annotation_counts: dict[str, int]) -> bool:
    return all(
        annotation_counts.get(annotation_type, 0) == 0
        for annotation_type in UNWANTED_ANNOTATION_TYPES
    )


def _has_highlight_when_expected(
    annotation_counts: dict[str, int],
    expected: object,
) -> bool:
    changes = _expected_changes(expected)

    if not changes:
        return annotation_counts.get("Highlight", 0) == 0

    revised_side_changes = [
        change for change in changes if change.get("type") in {"added", "modified"}
    ]

    if not revised_side_changes:
        return True

    return annotation_counts.get("Highlight", 0) > 0


def _contains_expected_revised_text(output_text: str, expected: object) -> bool:
    for change in _expected_changes(expected):
        revised_text = str(change.get("revised_text") or "").strip()

        if not revised_text:
            continue

        expected_highlight = str(change.get("expected_highlight") or "").strip()
        target = expected_highlight or revised_text

        if _normalize(target) not in _normalize(output_text):
            return False

    return True


def _expected_changes(expected: object) -> list[dict[str, Any]]:
    if not isinstance(expected, dict):
        return []

    changes = expected.get("expected_changes")

    if not isinstance(changes, list):
        return []

    return [change for change in changes if isinstance(change, dict)]


def _extract_pdf_text(pdf_path: Path) -> str:
    with fitz.open(pdf_path) as document:
        return "\n".join(page.get_text() for page in document)


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


if __name__ == "__main__":
    raise SystemExit(main())
