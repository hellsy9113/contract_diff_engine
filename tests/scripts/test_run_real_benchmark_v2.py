from __future__ import annotations

import sys
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import cast


def test_build_global_report_summarizes_v2_results() -> None:
    build_global_report = _build_global_report()

    report = build_global_report(
        [
            {
                "case_id": "case_0001",
                "status": "passed",
                "mutation_type": "number changed",
                "confidence": 0.9,
                "change_count": 1,
                "unwanted_annotation_count": 0,
                "dense_highlight_pages": [],
            },
            {
                "case_id": "case_0002",
                "status": "failed",
                "mutation_type": "amount changed",
                "confidence": 0.0,
                "change_count": 0,
                "unwanted_annotation_count": 2,
                "dense_highlight_pages": [1],
            },
        ]
    )

    assert report["total_cases"] == 2
    assert report["passed"] == 1
    assert report["failed"] == 1
    assert report["average_confidence"] == 0.45
    assert report["average_changes_per_case"] == 0.5
    assert report["unwanted_annotation_count"] == 2
    assert report["dense_highlight_pages"] == [{"case_id": "case_0002", "page": 1}]
    assert report["failures_by_mutation_type"] == {"amount changed": 1}


def _build_global_report() -> Callable[[list[dict[str, object]]], dict[str, object]]:
    scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
    sys.path.insert(0, str(scripts_dir))

    try:
        module = import_module("run_real_benchmark_v2")
    finally:
        sys.path.pop(0)

    return cast(
        Callable[[list[dict[str, object]]], dict[str, object]],
        module.build_global_report,
    )
