# Contract Diff Engine - Alignment Layer Architecture

## Purpose

The Alignment Layer answers one question:

> Which parts of the original contract correspond to which parts of the revised contract?

It does not decide whether a clause is modified, added, deleted, risky, or
important. It only creates a reliable mapping between parsed structures.

## Pipeline Position

```text
Original PDF -> Extraction -> Normalization -> Parsing -> StructuredDocument A
Revised PDF  -> Extraction -> Normalization -> Parsing -> StructuredDocument B

StructuredDocument A + StructuredDocument B
    -> Document Similarity Gate
    -> Alignment Layer
    -> Comparison Layer
    -> Annotation Layer
    -> Rendering Layer
    -> Frontend DTO / Annotated PDF
```

## Core Rules

The Alignment Layer must be:

```text
Deterministic
Rule-based
Testable
Explainable
Frontend-safe
```

It must not use AI, LLMs, embeddings, semantic legal reasoning, comparison
classification, annotation rendering, PDF rendering, or frontend code.

## Responsibilities

```text
1. Check whether the documents are similar enough to compare.
2. Match sections between original and revised documents.
3. Match clauses between original and revised documents.
4. Detect clauses that exist only in the original document.
5. Detect clauses that exist only in the revised document.
6. Provide revised-document anchors for deleted/original-only clauses.
7. Produce structured alignment results for the comparison layer.
```

## Alignment Statuses

```text
matched
original_only
revised_only
```

`matched` means a clause exists in both documents. The comparison layer later
decides whether it is unchanged or modified.

`original_only` means a clause exists only in the original document. The result
must include a revised anchor when one can be found, because removed text cannot
be highlighted directly in the revised PDF.

`revised_only` means a clause exists only in the revised document. The revised
clause anchors to itself.

## Document Similarity Gate

Before clause alignment starts, the layer checks whether the two documents are
similar enough to compare.

Default rule:

```text
MIN_DOCUMENT_SIMILARITY = 50.0

if document_similarity < MIN_DOCUMENT_SIMILARITY:
    return rejected result
else:
    continue alignment
```

Low similarity is a valid business outcome, not a system exception.

## Document-Level Similarity Formula

For v1:

```text
overall_similarity =
    40% heading similarity
  + 40% clause text similarity
  + 10% clause count similarity
  + 10% document length similarity
```

Document similarity answers:

```text
Are these two documents similar enough to compare?
```

Clause alignment similarity answers:

```text
Which revised clause best matches this original clause?
```

These concepts must remain separate.

## Clause Matching Formula

For v1:

```text
clause_alignment_score =
    30% clause number similarity
  + 25% text similarity
  + 20% section similarity
  + 15% heading similarity
  + 10% position similarity
```

Default rule:

```text
MIN_CLAUSE_MATCH_SCORE = 60.0
```

If a candidate pair scores below the threshold, it is not accepted as a match.

## Matching Algorithm

```text
1. Collect all original clauses.
2. Collect all revised clauses.
3. Score every original/revised clause pair.
4. Sort candidate pairs by score descending.
5. Greedily assign best non-conflicting matches.
6. Mark unmatched original clauses as original_only.
7. Mark unmatched revised clauses as revised_only.
8. Assign revised anchors for original_only clauses.
9. Return AlignmentResult.
```

Greedy matching is intentionally simple and inspectable for v1. A future
bipartite matcher can replace the assignment algorithm without changing the
output models.

## Revised Anchor Strategy

For removed/original-only clauses, choose an anchor in the revised document.

V1 priority:

```text
1. Previous matched revised clause
2. Next matched revised clause
3. No anchor, with warning
```

Later versions may add same-section and revised-section-heading fallbacks.

## Frontend Safety

Alignment output must be serializable and easy to transform into DTOs.

Allowed:

```text
IDs
strings
numbers
lists/tuples
plain JSON-safe nested structures
```

Forbidden:

```text
PyMuPDF objects
file handles
bytes
implicit Python object references
```

## Traceability

Every alignment decision preserves clause IDs. Those IDs connect back through:

```text
StructuredDocument
    -> NormalizedDocument
    -> ExtractedDocument
    -> PDF spans
    -> Bounding boxes
```

This chain is mandatory for PDF highlighting, frontend navigation, annotation
bubbles, metadata appendices, and debugging.

## Warnings

The layer should collect warnings instead of silently guessing.

Examples:

```text
LOW_MATCH_CONFIDENCE
MULTIPLE_SIMILAR_CANDIDATES
NO_REVISED_ANCHOR_FOUND
DOCUMENT_SIMILARITY_LOW_BUT_ALLOWED
SECTION_NOT_FOUND
```

## Final Output Contract

The rest of the engine should consume only:

```text
AlignmentResult
```

The comparison layer should not rerun matching. The annotation layer should not
guess missing anchors. The renderer should not decide whether clauses are added
or removed.
