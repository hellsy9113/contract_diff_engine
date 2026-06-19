# V2 Word-Level Diff

The v2 comparison path compares extracted PDF documents as ordered word-token
streams. It replaced the earlier paragraph-level diff because paragraph blocks are
too coarse for annotation and rendering: one changed word could cause an entire
paragraph to be classified as modified and highlighted in the output PDF.

## Why Paragraph-Level Diff Was Replaced

Paragraph-level comparison worked for broad smoke tests, but it created noisy
visual output:

- small word changes became full paragraph replacements
- page shifts could make unchanged text look inserted or modified
- deleted text had no precise revised-side anchor
- annotation popup text often contained long paragraph fragments
- highlights were too large for a reviewer to trust quickly

The renderer needs precise source metadata. Word-level diffing keeps each visible
token connected to its page, line, bounding box, and document-order index.

## Word Tokens

Extraction builds a `DocumentWordStream` for each PDF. The stream is continuous
across the whole document rather than page-by-page:

```text
page 1 tokens
page 2 tokens
page 3 tokens
...
```

Each `WordToken` preserves:

- visible text for display
- normalized text for matching
- page number
- bounding box
- line/block/paragraph IDs when available
- section heading when available
- full-document token index

Normalization is intentionally conservative. It trims whitespace, collapses
repeated whitespace, normalizes safe Unicode punctuation, and case-folds for
matching. It does not strip legal punctuation from display text.

## Diff Classification

The comparison layer runs a full-document sequence match over normalized word
tokens. It emits word operations:

- `equal`: tokens exist unchanged in both documents
- `insert`: tokens exist only in the revised document
- `delete`: tokens exist only in the original document
- `replace`: original tokens were replaced by revised tokens

Renderer-facing changes map these operations to the existing change types:

- `insert` -> `added`
- `delete` -> `deleted`
- `replace` -> `modified`

The public API and generated PDF response stay unchanged. The frontend still
uploads original and revised PDFs and receives an annotated revised PDF.

## Deleted Text

Deleted text does not exist in the revised PDF, so it cannot be highlighted at
its original coordinates on the revised visual base. Instead, v2 creates a small
red deletion marker anchored near the nearest surviving revised token:

1. prefer the revised token immediately after the deletion
2. otherwise use the revised token immediately before the deletion
3. otherwise fall back to original location metadata

The popup annotation represents the deleted content with a plain-text fallback:

```text
[DELETED: Public Key Infrastructure]
```

This is used because PDF popup annotations are plain text in the current
renderer. The internal annotation context still stores markdown-like display text
with `~~deleted text~~` for debugging and future rich annotation support.

## Annotation Context

Annotation context is built from structured token ranges, not raw paragraphs.
Each annotation tries to include:

- one unchanged word before the change
- the changed text
- one unchanged word after the change

Examples:

```text
[1]. [DELETED: Apart from Shor's algorithm...] It
```

```text
security ++guaranteeing these features++ mechanisms,
```

```text
provide [DELETED: advanced security features such as] advanced properties like unlinkability
```

Long changes are not expanded into unrelated paragraphs. If the changed content
itself is long, the annotation may still be long because the real edit is long.

## Rendering

Inserted and replacement tokens are rendered from revised-side token bounding
boxes. Adjacent tokens on the same line may be merged into compact highlight
rectangles. Rectangles are not merged across pages or lines.

Deleted operations render as small red underline markers at their revised-side
anchor. Equal tokens render nothing.

Optional development diagnostics can be generated with:

```bash
DEBUG_DIFF=true
```

or by passing the internal v2 service debug flag. This writes `diff-debug.json`
with token counts, change metadata, token ranges, highlight rectangle counts,
anchor boxes, and warnings for suspicious changes.

## Known Limitations

- Scanned PDFs without OCR may have little or no extractable text.
- Complex tables can produce noisy reading order and token grouping.
- Multi-column layouts are supported heuristically, not with a full layout model.
- Headers and footers are detected heuristically and may occasionally leak into
  comparison.
- Hyphenated line breaks can split legal terms or create cosmetic replacements.

## Future Improvements

- OCR fallback for scanned PDFs.
- Visual regression screenshots for generated annotated PDFs.
- Table-aware diffing with row and cell structure.
- Semantic clause grouping on top of the word-token diff.
- Rich-text popup rendering if the target PDF viewer support is reliable.
