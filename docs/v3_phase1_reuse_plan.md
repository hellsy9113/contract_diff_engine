# V3 Phase 1 Reuse Plan

This audit is Step 1 of the v3 clause JSON implementation plan. It does not
introduce v3 runtime behavior and does not change the working v2 engine.

## Current V2 Pipeline

The existing PDF flow is still:

```text
upload PDFs
  -> read upload bytes in FastAPI
  -> validate/profile/extract PDFs
  -> compare documents
  -> generate annotated PDF
  -> return/store output where the caller chooses
```

The active API path is:

1. `src/contract_diff_api/routes/compare.py`
   - `/compare` reads `original_file` and `revised_file`.
   - v2 is the default unless `CONTRACT_DIFF_COMPARE_ENGINE=v1` is set.
   - `_compare_v2_response()` returns `application/pdf` bytes.

2. `src/contract_diff/services/compare_v2.py`
   - profiles each PDF with `profile_pdf()`.
   - extracts each PDF with `extract_and_process_pdf()`.
   - builds document-level word streams.
   - compares word streams into renderer-ready `Change` objects.
   - renders annotations onto the revised PDF.
   - builds a `ComparisonReport`.

3. `src/contract_diff/rendering/pdf_renderer_v2.py`
   - opens the revised PDF binary.
   - renders highlights for inserted/replaced revised tokens.
   - renders small deletion anchors for deleted original tokens.
   - returns annotated PDF bytes.

Older v1/core orchestration still exists in
`src/contract_diff/core/services/contract_diff_engine.py`, but it is a
PDF-output engine and should not be the v3 endpoint implementation.

## SAFE_TO_REUSE

These modules are deterministic lower-level utilities and can be reused directly
by v3 without invoking the v2 PDF output pipeline.

| Area | Modules | Why safe |
| --- | --- | --- |
| API app conventions | `src/contract_diff_api/main.py`, `src/contract_diff_api/routes/compare.py` as style reference only | Shows router inclusion, response style, CORS conventions, and upload patterns. V3 should add a separate router rather than modifying `/compare`. |
| Format detection | `src/contract_diff/extraction/identification/format_detector.py` | Detects PDF magic bytes and preserves stream position. Useful for upload validation if v3 receives file-like streams. |
| Extraction exceptions | `src/contract_diff/extraction/exceptions/extraction.py` | Reusable error vocabulary: `ExtractionError`, `UnsupportedFormatError`, `InvalidDocumentError`, `CorruptedDocumentError`, `ExtractionFailedError`. |
| Structured PDF extraction | `src/contract_diff/extraction/structured/structured_pdf_reader.py` | Opens PDF bytes with PyMuPDF and returns pages, blocks, lines, spans, words, text, and geometry without comparing or rendering. |
| Structured extraction pipeline | `src/contract_diff/extraction/structured/pipeline.py` | `extract_and_process_pdf()` adds reading order, column detection, block classification, section paths, warnings, and word tokens. This is the best v3 adapter target. |
| PDF profiling | `src/contract_diff/extraction/structured/pdf_profiler.py` | Can provide validation/quality warnings such as encrypted/scanned/table/column signals. It does not compare or render. |
| Structured extraction models | `src/contract_diff/extraction/structured/models.py` | `StructuredDocument`, `ExtractedPage`, `TextBlock`, `TextLine`, `TextSpan`, `ExtractedWord`, `WordToken`, `DocumentWordStream`, and `PdfIntakeReport` are safe read-only extraction outputs. |
| Existing document DOM | `src/contract_diff/models/document/*` | `ExtractedDocument`, `Page`, `Block`, `Line`, `Span`, `BoundingBox`, and `DocumentMetadata` are canonical extraction models. Useful if v3 later needs canonical metadata. |
| Normalization utilities | `src/contract_diff/normalization/utils/text_normalizer.py` and `src/contract_diff/comparison/utils/text_diff_helpers.py` | Useful for safe whitespace/punctuation normalization and similarity. V3 should use these utilities, not rendering-specific fragments. |
| Similarity helpers | `src/contract_diff/alignment/scoring/text_similarity.py`, parts of `src/contract_diff/comparison/utils/text_diff_helpers.py` | Safe for clause text similarity if imported as pure functions. V3 should still own its clause-alignment model/output. |

## REUSE_WITH_ADAPTER

These modules contain useful behavior but their current shape is not the v3 API
shape. V3 should wrap or adapt them instead of calling the full workflow.

| Area | Modules | Adapter guidance |
| --- | --- | --- |
| PDF extraction service | `src/contract_diff/extraction/services/extraction_service.py`, `src/contract_diff/extraction/readers/pdf/pdf_reader.py` | Useful if v3 wants canonical `ExtractedDocument`. However, the structured pipeline currently gives better page/block/word data for clause extraction. Prefer a v3 `document_text_adapter.py` around `extract_and_process_pdf()`. |
| Text normalization service | `src/contract_diff/normalization/services/normalization_service.py` | Built around canonical `ExtractedDocument` and source span IDs. V3 can reuse concepts/utilities but should return v3-only document text models. |
| Parsing detectors/rules | `src/contract_diff/parsing/detectors/*`, `src/contract_diff/parsing/rules/*` | Useful as references for headings, clause numbers, lists, and page artifacts. The existing parser returns v1/v2 parsing models, so v3 should implement a separate clause extractor over `V3DocumentText`. |
| Alignment scorers | `src/contract_diff/alignment/scoring/*` | Pure scoring functions can help v3 fuzzy matching. Existing `AlignmentService` returns v2/core alignment models and includes similarity gate behavior not required by v3 JSON. |
| Word token extraction | `src/contract_diff/extraction/structured/word_tokens.py`, `src/contract_diff/extraction/structured/word_stream.py` | Safe if v3 later needs geometry-aware token streams. Phase 1 v3 JSON can start from text, but should not call v2 rendering metadata. |
| Debug conventions | `src/contract_diff/debugging/diff_debug.py` | Useful as a reference for safe debug output. V3 should define a v3-specific debug model and avoid local paths. |

## V2_ONLY_DO_NOT_TOUCH

These modules are tied to annotated PDF output or existing v2 behavior. V3 must
not call or rewrite them for the clause JSON endpoint.

| Area | Modules | Reason |
| --- | --- | --- |
| V2 service | `src/contract_diff/services/compare_v2.py` | Ends in annotated PDF bytes and `ComparisonReport`. V3 must not call it because v3 returns JSON only and must not generate PDFs. |
| V2 renderer | `src/contract_diff/rendering/pdf_renderer_v2.py` | Opens and writes PDF annotations. V3 must not render PDFs. |
| Rendering services | `src/contract_diff/rendering/services/*` | All produce or support visual PDF output. Out of scope for v3 Phase 1. |
| Rendering styles/utils | `src/contract_diff/rendering/styles/*`, `src/contract_diff/rendering/utils/pdf_rects.py`, `src/contract_diff/rendering/utils/token_bboxes.py`, `src/contract_diff/rendering/utils/visual_fragments.py` | Tied to PDF annotation placement and search. V3 JSON should not depend on PDF rendering. |
| Annotation layer | `src/contract_diff/annotation/*` | Builds `AnnotationPlan` and rendering targets. V3 returns clause diff JSON, not annotation plans. |
| Reporting layer | `src/contract_diff/reporting/comparison_report.py` | Reports v2 PDF quality/rendering diagnostics. V3 needs a JSON summary model instead. |
| Core PDF-output engine | `src/contract_diff/core/services/contract_diff_engine.py` | Full v1/core orchestration ends in `RenderedDocument`. Useful as architecture reference only. |
| Existing `/compare` route | `src/contract_diff_api/routes/compare.py` | Must remain compatible. V3 should add a new router at `/v3/compare/clauses`. |
| Benchmark PDF runners | `scripts/run_real_benchmark.py`, `scripts/run_real_benchmark_v2.py` | Write `output.pdf` and PDF reports. V3 may get its own benchmark later, but should not alter these flows. |

## NEW_V3_REQUIRED

V3 should be implemented beside v2 in a separate package:

```text
src/contract_diff/v3/
  models/
  extraction/
  alignment/
  comparison/
  routes/
```

Required new v3 modules:

- `v3/models/document.py`
  - `V3PageText`
  - `V3DocumentText`
- `v3/models/clause.py`
  - `V3ExtractedClause`
  - `V3ClauseAlignment`
- `v3/models/diff.py`
  - `V3DiffToken`
  - `V3ClauseDiff`
- `v3/models/response.py`
  - `V3CompareSummary`
  - `V3ClauseCompareResponse`
  - later `V3DebugInfo`
- `v3/extraction/document_text_adapter.py`
  - wraps `extract_and_process_pdf()` and converts structured extraction to
    v3 page/full text models.
- `v3/extraction/clause_extractor.py`
  - detects numbered clauses and headings from `V3DocumentText`.
- `v3/alignment/clause_aligner.py`
  - aligns v3 clauses by number and text similarity, not page number.
- `v3/comparison/word_diff.py`
  - emits frontend-ready `equal`/`insert`/`delete` tokens.
- `v3/comparison/clause_compare_service.py`
  - orchestrates v3 extraction, clause extraction, alignment, word diff, and
    summary counts.
- `v3/routes/compare_clauses.py`
  - exposes `POST /v3/compare/clauses` and returns JSON only.

## Audit Answers

1. PDF validation is currently handled by:
   - `FormatDetector.detect()` for signature-level format detection.
   - `PdfReader.can_read()` for stream-based PDF readability.
   - `profile_pdf()` for structured PDF quality/validity reporting.
   - `extract_structured_pdf()` for extraction-time invalid/encrypted PDF errors.

2. Upload handling is currently in:
   - `src/contract_diff_api/routes/compare.py`, which reads FastAPI
     `UploadFile` objects into bytes.
   - There is no required temporary-file layer for current API comparison; v2
     operates on bytes. Benchmark scripts choose their own disk output paths.

3. PDF text extraction is handled by:
   - `extract_structured_pdf()` for raw structured pages/blocks/words.
   - `extract_and_process_pdf()` for processed structured extraction with
     reading order, classification, sections, warnings, and word tokens.
   - `PdfReader.extract()` for canonical DOM extraction.

4. Extracted documents/pages are represented by:
   - structured models in `src/contract_diff/extraction/structured/models.py`:
     `StructuredDocument`, `ExtractedPage`, `TextBlock`, `TextLine`,
     `TextSpan`, `ExtractedWord`, and `WordToken`.
   - canonical DOM models in `src/contract_diff/models/document/*`:
     `ExtractedDocument`, `Page`, `Block`, `Line`, `Span`, `BoundingBox`, and
     `DocumentMetadata`.

5. Text normalization utilities are:
   - `TextNormalizer.normalize()` for safe whitespace and Unicode normalization.
   - `normalize_for_alignment()` in
     `src/contract_diff/comparison/utils/text_diff_helpers.py` for matching.
   - `normalize_word_token_text()` in structured word-token extraction for
     word-level matching.

6. Reusable exceptions are in:
   - `src/contract_diff/extraction/exceptions/extraction.py`.

7. Modules tied to v2 annotation rendering are:
   - `src/contract_diff/rendering/pdf_renderer_v2.py`
   - `src/contract_diff/rendering/services/*`
   - `src/contract_diff/rendering/styles/*`
   - `src/contract_diff/rendering/utils/*`
   - `src/contract_diff/annotation/*`

8. Modules tied to v2 paragraph/block-level comparison are:
   - legacy/current tests and fallback code around
     `src/contract_diff/alignment/structured_alignment.py`
   - `src/contract_diff/comparison/structured_changes.py`
   - `src/contract_diff/comparison/services/text_unit_comparison_service.py`
   - `src/contract_diff/comparison/token_diff.py`

   Note: the active `compare_v2.py` path now uses document-level word diffing
   through `src/contract_diff/comparison/word_diff.py`, but v3 should still own
   its response models and not call the v2 service.

9. V3 should reuse:
   - `extract_and_process_pdf()` through a v3 document text adapter.
   - structured extraction models for source text/page order.
   - `profile_pdf()` or extraction exceptions for validation/error reporting.
   - pure normalization/similarity helpers where they fit.
   - FastAPI app/router conventions.

10. V3 must not call:
   - `compare_pdf_bytes_v2()`
   - `render_changes_to_pdf()`
   - `PdfRenderingService.render()`
   - annotation builder/target resolver services
   - `ContractDiffEngine.compare()` for the v3 JSON endpoint
   - v2 benchmark runners or PDF storage/output code

## Step 2 Recommendation

Start v3 implementation with a read-only adapter:

```python
extract_document_text_v3(pdf_bytes: bytes, filename: str | None = None) -> V3DocumentText
```

The adapter should call `extract_and_process_pdf(pdf_bytes)`, preserve page
numbers, join page text in page order, and set `title=None` until reliable title
metadata is available through the structured extraction path.

This keeps v3 independent from v2 comparison/rendering while avoiding duplicate
PDF extraction logic.
