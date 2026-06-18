# Contract Diff Engine

A Python 3.12 contract comparison engine that returns an annotated revised PDF.

The engine compares an original PDF and a revised PDF, detects meaningful
contract text changes, and renders visual highlights/markers onto the revised
document. The FastAPI adapter is intentionally thin; the core comparison logic
lives under `src/contract_diff`.

## Pipeline

```text
Original PDF + Revised PDF
        |
        v
Extraction -> Normalization -> Parsing -> Similarity Gate
        -> Alignment -> Comparison -> Annotation Plan -> Rendering
        |
        v
Annotated revised PDF
```

The document model preserves page/block/line/span IDs and bounding boxes so
rendering can map detected changes back to PDF coordinates.

## Current Rendering Behavior

- Added text: soft green highlights.
- Modified text: soft amber highlights on changed revised-side fragments.
- Deleted text: small red left-margin underline marker near the revised anchor.
- Unchanged text: no annotation.
- Appendix generation is currently disabled in the main renderer until a compact
  layout is implemented.
- `Text`, `Square`, `FreeText`, and `Rect` annotations are not used in the main
  rendering path.

## API

Run locally:

```bash
uv run uvicorn contract_diff_api.main:app --reload
```

Compare two PDFs:

```bash
curl -X POST "http://127.0.0.1:8000/compare" \
  -F "original_file=@original.pdf;type=application/pdf" \
  -F "revised_file=@revised.pdf;type=application/pdf" \
  --output annotated.pdf
```

Successful comparisons return `application/pdf`. Low-similarity or failed
comparisons return JSON.

## Diagnostics

Compare and inspect rendering output:

```bash
uv run python scripts/diagnose_compare.py original.pdf revised.pdf
```

Inspect an already rendered PDF:

```bash
uv run python scripts/diagnose_visuals.py annotated.pdf
```

Diagnostics report highlight counts, unwanted annotation counts, dense pages,
and whether the output contains revised-only text.

## Real Dataset Benchmark

CUAD is the first supported real-contract source. The local benchmark pipeline
does not fine-tune or train models; it uses real contract text as source
material and creates deterministic original/revised PDF pairs with expected
changes.

Ingest CUAD:

```bash
uv run python scripts/ingest_cuad.py
```

If the optional Hugging Face `datasets` package is unavailable, provide a local
CUAD folder:

```bash
uv run python scripts/ingest_cuad.py --local-cuad-dir /path/to/cuad
```

Build benchmark cases:

```bash
uv run python scripts/build_real_benchmark_from_cuad.py
```

Run the benchmark:

```bash
uv run python scripts/run_real_benchmark.py
```

Outputs live under:

```text
datasets/raw/cuad/
datasets/real_benchmark_v1/cuad/
```

## Quality Checks

```bash
uv run ruff check .
uv run mypy src tests
uv run pytest -v
```

The scripts are also type-checkable:

```bash
MYPYPATH=src uv run mypy scripts --strict --ignore-missing-imports
```
