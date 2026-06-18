# Comparison Layer Architecture

The comparison layer sits after alignment and before annotation/rendering.

It is an internal engine layer. It is not connected directly to the frontend.
The final external behavior remains:

```text
Frontend sends:
    original PDF binary
    revised PDF binary

Engine returns:
    annotated revised PDF binary stream

Only if rejected:
    JSON warning
```

The comparison layer does not return frontend JSON. It produces internal change
records that the annotation and rendering layers will use to generate the final
PDF.

## Pipeline Position

```text
Original PDF + Revised PDF
        ↓
Extraction
        ↓
Normalization
        ↓
Parsing
        ↓
Document Similarity Gate
        ↓
Alignment
        ↓
Comparison
        ↓
Annotation Builder
        ↓
PDF Renderer
        ↓
Annotated PDF Binary Stream
```

## Responsibility

The comparison layer answers:

> Given the alignment result, what type of change happened?

It converts alignment statuses into comparison change types:

```text
matched       -> unchanged or modified
original_only -> removed
revised_only  -> added
```

## The Layer Should Do

```text
1. Inspect aligned clauses.
2. Determine whether matched clauses are unchanged or modified.
3. Mark original-only clauses as removed.
4. Mark revised-only clauses as added.
5. Generate fragment-level text differences for modified clauses.
6. Preserve clause IDs, source references, and revised anchors.
7. Produce internal ComparisonResult for annotation/rendering.
```

## The Layer Should Not Do

```text
No AI
No legal reasoning
No risk scoring
No PDF rendering
No annotation color decision
No frontend DTO generation
No clause alignment
No bounding-box drawing
```

## Input Contract

```python
ComparisonService.compare(
    original_document: StructuredDocument,
    revised_document: StructuredDocument,
    alignment_result: AlignmentResult,
)
```

The comparison layer trusts the alignment layer. It must not re-match clauses.

## Output Contract

```text
ComparisonResult
├── compared_clauses
├── summary
└── warnings
```

This is consumed by:

```text
Annotation Builder
PDF Renderer
Report Generator later
Tests/debugging
```

## Change Types

```text
unchanged
modified
added
removed
```

## Fragment Operations

```text
equal
inserted
deleted
replaced
```

The renderer now consumes revised-side inserted fragments for modified changes
and avoids highlighting entire paragraphs when only a phrase changed. The
comparison layer still does not decide colors or PDF geometry; it only preserves
the fragment data needed by rendering.

## Text Equivalence

Current equivalence:

```text
- collapse whitespace
- trim spaces
- casefold for matching
- normalize smart quotes and common hyphen variants
```

Normalization is used for matching/alignment decisions only. User-facing text
and rendering search text continue to use extracted source text.

## Diff Algorithm

Use Python standard library `difflib.SequenceMatcher` with word-level units.
Word-level diffs are cleaner for legal text than character-level diffs.

## Warnings

Warnings should not necessarily stop the pipeline.

Examples:

```text
MISSING_ORIGINAL_CLAUSE
MISSING_REVISED_CLAUSE
MISSING_REVISED_ANCHOR
EMPTY_ORIGINAL_TEXT
EMPTY_REVISED_TEXT
NO_TEXT_DIFF_FOR_MODIFIED_CLAUSE
```

## Final Rule

The comparison layer should produce only:

```text
This clause is unchanged.
This clause is modified.
This clause was added.
This clause was removed.
These text fragments changed.
```

It must not decide:

```text
Which color to use
Where to draw on the PDF
How the popup looks
What the frontend receives
Whether a change is risky
```

Those belong to later layers.
