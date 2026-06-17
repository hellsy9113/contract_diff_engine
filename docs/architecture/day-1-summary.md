# Contract Diff Engine — Architecture Summary (Day 1)

## Project Vision

The project is no longer a traditional contract diff tool that generates a report.

The primary output is:

> An annotated version of the revised PDF that visually highlights modifications, deletions, and review comments directly inside the document.

The report becomes a secondary artifact.

---

# Final Product Workflow

```text
Original PDF
        \
         \
          --> Engine --> Annotated Revised PDF
         /
        /
Revised PDF
```

Output:

* Yellow highlights → Modified clauses
* Red highlights → Removed clauses
* No highlight → Unchanged clauses
* Annotation bubble → Original clause text
* Metadata appendix → Page number, heading, section, etc.
* Unique annotation IDs

---

# Revised Engine Architecture

```text
Extraction
    ↓
Structural Parsing
    ↓
Alignment
    ↓
Comparison
    ↓
Annotation Builder
    ↓
PDF Renderer
    ↓
Annotated PDF

(Optional)
    ↓
Report Generator
```

---

# Technology Decisions

## Language

Python 3.12

Reason:

* Best NLP ecosystem
* Best document processing ecosystem
* Future AI integration

---

## Package Manager

uv

Reason:

* Fast
* Modern
* Lock files
* Excellent dependency management

---

## API Layer (Future)

FastAPI

Important:

The engine itself should remain independent of FastAPI.

Architecture:

```text
Next.js
      │
      ▼
FastAPI
      │
      ▼
Contract Engine
```

---

# Repository Structure

```text
contract-diff-engine/

├── docs/
├── scripts/
├── src/
│   └── contract_diff/
│
├── tests/
│
├── README.md
├── pyproject.toml
└── .gitignore
```

---

# Extraction Architecture

Extraction follows a plugin-based design.

```text
Binary Stream
      │
      ▼
Format Detector
      │
      ▼
DocumentFormat
      │
      ▼
Reader Registry
      │
      ▼
Document Reader
      │
      ▼
ExtractedDocument
```

---

# Format Detection Strategy

Detection order:

```text
Magic Bytes
      │
      ▼
PDF ?

YES -> PDF

NO
      │
      ▼
ZIP ?

YES -> DOCX

NO
      │
      ▼
UTF-8 ?

YES -> TXT

NO
      │
      ▼
UNKNOWN
```

Rules:

* Never trust file extension
* Use file signature first
* TXT is fallback
* Unsupported formats become UNKNOWN

---

# Extraction Components Implemented

## DocumentFormat

```text
PDF
DOCX
TXT
UNKNOWN
```

---

## Exceptions

```text
ExtractionError

├── UnsupportedFormatError
├── InvalidDocumentError
├── CorruptedDocumentError
└── ExtractionFailedError
```

---

## Reader Interface

```text
DocumentReader

supported_format

can_read()

extract()
```

All readers implement the same contract.

---

## Reader Registry

Responsibilities:

```text
Register Reader
Get Reader
Supports Format
List Supported Formats
```

---

## TXT Reader

Implemented.

Responsibilities:

* Decode UTF-8
* Create metadata
* Create page
* Return ExtractedDocument

Not responsible for:

* Cleaning
* Parsing
* Comparing

---

## Extraction Service

Orchestrates:

```text
Format Detection
        ↓
Registry Lookup
        ↓
Capability Check
        ↓
Reader Extraction
```

Contains no extraction logic itself.

---

# Current Extraction Package Structure

```text
extraction/

├─ enums/
│  └─ document_format.py
│
├─ exceptions/
│  └─ extraction.py
│
├─ identification/
│  └─ format_detector.py
│
├─ interfaces/
│  └─ reader.py
│
├─ models/
│  ├─ extracted_document.py
│  ├─ metadata.py
│  └─ page.py
│
├─ readers/
│  ├─ docx/
│  ├─ pdf/
│  └─ txt/
│
├─ registry/
│  └─ reader_registry.py
│
└─ services/
   └─ extraction_service.py
```

---

# Testing Status

Current status:

```text
19 Tests Passing
```

Coverage includes:

* Format Detector
* Reader Registry
* TXT Reader
* Extraction Service

Output:

```text
====================
19 passed
====================
```

Extraction architecture is stable.

---

# Major Architectural Change

The project is shifting from:

```text
Contract Diff Engine
```

to:

```text
Document Review Engine
```

Core value:

Generate a lawyer-friendly review version of the revised contract.

---

# Planned Document Object Model (DOM)

Current models are considered Version 1.

Version 2 will introduce a rich document model.

```text
ExtractedDocument
│
├── metadata
│
└── pages
      │
      └── blocks
            │
            └── lines
                  │
                  └── spans
```

---

# Planned Models

```text
bounding_box.py

span.py

line.py

block.py

page.py

metadata.py

extracted_document.py
```

---

# Bounding Box Model

```text
x0
y0
x1
y1
```

Purpose:

Support PDF annotations and highlighting.

---

# Span Model

Smallest renderable unit.

```text
text
bbox
font
font_size
flags
```

Future renderer highlights spans.

---

# Why Rich PDF Extraction?

The renderer will need:

```text
Text
+
Coordinates
+
Layout
```

Example:

```text
"30 days"

bbox=(...)
```

Without coordinates, annotations cannot be rendered accurately.

---

# Accepted Annotation Design

Each annotation receives a unique ID.

Example:

```text
Annotation #12
```

PDF:

```text
[12]
```

Appendix:

```text
Annotation 12

Page: 8

Heading: Payment Terms

Original Clause:
...

Modified Clause:
...
```

Benefits:

* Traceability
* Navigation
* Lawyer-friendly review process

---

# Current Roadmap

## Milestone 1

Document Object Model (DOM) v2

Implement:

```text
BoundingBox
Span
Line
Block
Page
ExtractedDocument
```

---

## Milestone 2

Production PDF Reader

Using:

```text
PyMuPDF
```

Responsibilities:

* Metadata extraction
* Page extraction
* Layout extraction
* Bounding box extraction
* Reading order preservation

---

## Milestone 3

PDF Extraction Tests

Validate:

* Metadata
* Text
* Pages
* Coordinates
* Corrupted documents
* Encrypted documents

---

## Milestone 4

Structural Parser

Convert:

```text
ExtractedDocument
      ↓
StructuredDocument
```

Detect:

* Headings
* Sections
* Clauses

---

## Milestone 5

Alignment Engine

Match:

```text
Clause A
      ↔
Clause B
```

Across contract versions.

---

## Milestone 6

Difference Engine

Generate:

```text
Modified
Deleted
Unchanged
```

Clause states.

---

## Milestone 7

Annotation Builder

Generate annotation objects.

---

## Milestone 8

PDF Renderer

Generate annotated PDF.

---

# Current Priority

Next task:

> Design and implement Document Object Model (DOM) Version 2 before implementing PdfReader.

Reason:

Every future layer (parsing, alignment, comparison, annotation, rendering) will depend on this model.
