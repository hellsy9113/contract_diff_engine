# Annotation Layer Architecture

The annotation layer sits after comparison and before rendering:

```text
Extraction
  -> Normalization
  -> Parsing
  -> Alignment
  -> Comparison
  -> Annotation
  -> Rendering
```

Its job is to convert a `ComparisonResult` into an `AnnotationPlan`. It does not
open PDFs, draw highlights, write binary streams, align clauses, compare text, or
call the frontend.

## Responsibility

The comparison layer decides whether a clause is `unchanged`, `modified`,
`added`, or `removed`.

The annotation layer decides what the renderer should do with those changes:

| Change type | Annotation behavior |
| --- | --- |
| `unchanged` | No annotation |
| `modified` | Highlight the revised clause |
| `added` | Highlight the revised clause |
| `removed` | Place a deletion marker near the revised anchor clause |

## Traceability

Annotation instructions preserve source span IDs from the revised document. The
renderer later resolves those span IDs to bounding boxes and draws the final PDF
annotations.

```text
ComparedClause
  -> AnnotationItem
  -> AnnotationTarget
  -> source_span_ids
  -> renderer bounding boxes
```

## Models

`AnnotationTarget` represents where an annotation attaches in the revised PDF.
For modified and added clauses, the target is the revised clause. For removed
clauses, the target is the revised anchor clause.

`AnnotationItem` is the renderer-facing instruction. It contains the annotation
type, style, target, source texts, popup text, heading, fragments, and warnings.

`AnnotationAppendixEntry` stores metadata that can later be rendered into an
appendix or end section.

`AnnotationPlan` is the top-level output consumed by the rendering layer. It
contains annotation items, appendix entries, summary counts, and warnings.

## Styles

The annotation layer names semantic styles only:

| Change type | Highlight style |
| --- | --- |
| `modified` | `modified_highlight` |
| `added` | `added_highlight` |
| `removed` | `removed_marker` |

The rendering layer maps those styles to actual PDF colors and drawing behavior.
