from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from textwrap import wrap

import fitz

UNWANTED_ANNOTATION_TYPES = {"Text", "Square", "FreeText", "Rect"}
ALLOWED_VISUAL_ANNOTATION_TYPES = {"Highlight", "Underline", "StrikeOut"}

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_COMMON_NOISE_WORDS = {"page", "signature", "exhibit", "schedule"}
_JURISDICTIONS = (
    "Delaware",
    "California",
    "New York",
    "Texas",
    "England",
    "India",
    "Singapore",
)
_PARTY_TERMS = (
    "Company",
    "Buyer",
    "Seller",
    "Supplier",
    "Customer",
    "Client",
    "Licensee",
    "Licensor",
    "Borrower",
    "Lender",
)
_PERIOD_KEYWORDS = (
    "confidential",
    "confidentiality",
    "termination",
    "liability",
    "indemnity",
    "notice",
)


@dataclass(frozen=True)
class ExpectedChange:
    type: str
    original_text: str
    revised_text: str
    expected_highlight: str
    should_not_highlight: list[str]


@dataclass(frozen=True)
class MutationResult:
    mutation_type: str
    description: str
    original_text: str
    revised_text: str
    expected_change: ExpectedChange


def make_pdf_from_text(text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    x = 72
    y = 72
    line_height = 14
    bottom_margin = 72

    for paragraph in text.splitlines():
        if not paragraph.strip():
            y += line_height
            continue

        for line in wrap(paragraph, width=88):
            if y > page.rect.height - bottom_margin:
                page = document.new_page(width=595, height=842)
                y = 72

            page.insert_text((x, y), line, fontsize=10.5)
            y += line_height

        y += line_height

    document.save(output_path)
    document.close()


def extract_candidate_paragraphs(text: str) -> list[str]:
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_parts = re.split(r"\n\s*\n|(?<=\.)\n(?=[A-Z0-9])", normalized_text)
    candidates: list[str] = []

    for part in raw_parts:
        paragraph = _normalize_space(part)

        if _is_usable_paragraph(paragraph):
            candidates.append(paragraph)

    return candidates


def mutate_paragraph(
    paragraph: str,
    preferred_mutation: str | None = None,
) -> MutationResult | None:
    mutation_builders = {
        "amount changed": _mutate_amount,
        "date changed": _mutate_date,
        "number changed": _mutate_number,
        "party name changed": _mutate_party_name,
        "jurisdiction changed": _mutate_jurisdiction,
        "sentence added": _mutate_sentence_added,
        "sentence deleted": _mutate_sentence_deleted,
        "phrase modified": _mutate_phrase_modified,
        "clause deleted": _mutate_clause_deleted,
        "confidentiality period changed": _mutate_confidentiality_period,
        "termination period changed": _mutate_termination_period,
        "liability cap changed": _mutate_liability_cap,
    }

    if preferred_mutation is not None:
        return mutation_builders[preferred_mutation](paragraph)

    for builder in mutation_builders.values():
        result = builder(paragraph)

        if result is not None:
            return result

    return None


def write_expected_json(
    output_path: Path,
    case_id: str,
    source_dataset: str,
    description: str,
    expected_changes: list[ExpectedChange],
) -> None:
    payload = {
        "case_id": case_id,
        "source_dataset": source_dataset,
        "description": description,
        "expected_changes": [asdict(change) for change in expected_changes],
    }
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def count_pdf_annotations(pdf_path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}

    with fitz.open(pdf_path) as document:
        for page in document:
            annotation = page.first_annot

            while annotation is not None:
                annotation_type = annotation.type[1]
                counts[annotation_type] = counts.get(annotation_type, 0) + 1
                annotation = annotation.next

    return counts


def build_case_document(paragraph: str) -> str:
    return "\n\n".join(
        (
            "Benchmark excerpt derived from a real contract source.",
            paragraph,
            "All other terms and conditions remain in full force and effect.",
        )
    )


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _is_usable_paragraph(paragraph: str) -> bool:
    if len(paragraph) < 180 or len(paragraph) > 1400:
        return False

    if _mostly_numbers(paragraph):
        return False

    lowered = paragraph.casefold()

    if sum(1 for word in _COMMON_NOISE_WORDS if word in lowered) >= 3:
        return False

    alpha_chars = sum(1 for char in paragraph if char.isalpha())

    if alpha_chars / max(1, len(paragraph)) < 0.45:
        return False

    return paragraph.count(" ") >= 30


def _mostly_numbers(text: str) -> bool:
    numeric_chars = sum(1 for char in text if char.isdigit())
    alpha_chars = sum(1 for char in text if char.isalpha())
    return numeric_chars > alpha_chars


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _expected(
    change_type: str,
    original_text: str,
    revised_text: str,
    expected_highlight: str,
    unchanged_source: str,
) -> ExpectedChange:
    return ExpectedChange(
        type=change_type,
        original_text=original_text,
        revised_text=revised_text,
        expected_highlight=expected_highlight,
        should_not_highlight=_should_not_highlight(unchanged_source),
    )


def _should_not_highlight(text: str) -> list[str]:
    words = text.split()
    snippets: list[str] = []

    if len(words) >= 10:
        snippets.append(" ".join(words[:8]))

    if len(words) >= 18:
        midpoint = len(words) // 2
        snippets.append(" ".join(words[midpoint : midpoint + 8]))

    return snippets


def _result(
    mutation_type: str,
    description: str,
    original: str,
    revised: str,
    change_type: str,
    expected_highlight: str,
) -> MutationResult:
    return MutationResult(
        mutation_type=mutation_type,
        description=description,
        original_text=original,
        revised_text=revised,
        expected_change=_expected(
            change_type=change_type,
            original_text=original,
            revised_text=revised,
            expected_highlight=expected_highlight,
            unchanged_source=original,
        ),
    )


def _replace_first(text: str, old: str, new: str) -> str:
    return text.replace(old, new, 1)


def _mutate_amount(paragraph: str) -> MutationResult | None:
    match = re.search(r"(?:US\$|\$|USD\s*)\s?\d[\d,]*(?:\.\d+)?", paragraph)

    if match is None:
        return None

    original_value = match.group(0)
    revised_value = "$250,000" if "$250,000" not in original_value else "$500,000"
    revised = _replace_first(paragraph, original_value, revised_value)
    return _result(
        "amount changed",
        "Changed a monetary amount in a real CUAD paragraph.",
        paragraph,
        revised,
        "modified",
        revised_value,
    )


def _mutate_date(paragraph: str) -> MutationResult | None:
    month_pattern = "|".join(_MONTHS)
    match = re.search(
        rf"\b(?:{month_pattern})\s+\d{{1,2}},\s+\d{{4}}\b|\b\d{{1,2}}/\d{{1,2}}/\d{{2,4}}\b",
        paragraph,
    )

    if match is None:
        return None

    revised_value = "January 1, 2030"
    revised = _replace_first(paragraph, match.group(0), revised_value)
    return _result(
        "date changed",
        "Changed a date in a real CUAD paragraph.",
        paragraph,
        revised,
        "modified",
        revised_value,
    )


def _mutate_number(paragraph: str) -> MutationResult | None:
    match = re.search(r"(?<![\w.])(?:[2-9]|[1-9]\d|[1-9]\d{2})(?![\w.])", paragraph)

    if match is None:
        return None

    revised_value = "45" if match.group(0) != "45" else "60"
    revised = _replace_first(paragraph, match.group(0), revised_value)
    return _result(
        "number changed",
        "Changed a standalone number in a real CUAD paragraph.",
        paragraph,
        revised,
        "modified",
        revised_value,
    )


def _mutate_party_name(paragraph: str) -> MutationResult | None:
    for term in _PARTY_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", paragraph):
            revised = re.sub(
                rf"\b{re.escape(term)}\b",
                "Counterparty",
                paragraph,
                count=1,
            )
            return _result(
                "party name changed",
                "Changed a party reference in a real CUAD paragraph.",
                paragraph,
                revised,
                "modified",
                "Counterparty",
            )

    return None


def _mutate_jurisdiction(paragraph: str) -> MutationResult | None:
    for jurisdiction in _JURISDICTIONS:
        if re.search(rf"\b{re.escape(jurisdiction)}\b", paragraph):
            revised_value = "Delaware" if jurisdiction != "Delaware" else "New York"
            revised = re.sub(
                rf"\b{re.escape(jurisdiction)}\b",
                revised_value,
                paragraph,
                count=1,
            )
            return _result(
                "jurisdiction changed",
                "Changed a jurisdiction reference in a real CUAD paragraph.",
                paragraph,
                revised,
                "modified",
                revised_value,
            )

    return None


def _mutate_sentence_added(paragraph: str) -> MutationResult:
    added_sentence = " The parties shall cooperate in good faith during review."
    revised = f"{paragraph}{added_sentence}"
    return _result(
        "sentence added",
        "Added one sentence to a real CUAD paragraph.",
        paragraph,
        revised,
        "added",
        added_sentence.strip(),
    )


def _mutate_sentence_deleted(paragraph: str) -> MutationResult | None:
    sentences = _sentences(paragraph)

    if len(sentences) < 2:
        return None

    removed = sentences[-1]
    revised = _normalize_space(paragraph.replace(removed, "", 1))
    return _result(
        "sentence deleted",
        "Deleted one sentence from a real CUAD paragraph.",
        paragraph,
        revised,
        "deleted",
        "",
    )


def _mutate_phrase_modified(paragraph: str) -> MutationResult:
    phrase = "commercially reasonable efforts"

    if re.search(r"\breasonable efforts\b", paragraph, re.IGNORECASE):
        revised = re.sub(
            r"\breasonable efforts\b",
            phrase,
            paragraph,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        sentences = _sentences(paragraph)
        first_sentence = sentences[0] if sentences else paragraph
        revised_first = f"{first_sentence} The obligation is material."
        revised = _replace_first(paragraph, first_sentence, revised_first)
        phrase = "The obligation is material."

    return _result(
        "phrase modified",
        "Modified a phrase in a real CUAD paragraph.",
        paragraph,
        revised,
        "modified",
        phrase,
    )


def _mutate_clause_deleted(paragraph: str) -> MutationResult:
    return _result(
        "clause deleted",
        "Deleted a real CUAD paragraph from the revised benchmark PDF.",
        paragraph,
        "",
        "deleted",
        "",
    )


def _mutate_confidentiality_period(paragraph: str) -> MutationResult | None:
    if not re.search(r"confidential", paragraph, re.IGNORECASE):
        return None

    return _mutate_period(
        paragraph,
        "confidentiality period changed",
        "Changed a confidentiality period in a real CUAD paragraph.",
    )


def _mutate_termination_period(paragraph: str) -> MutationResult | None:
    if not re.search(r"terminat|notice", paragraph, re.IGNORECASE):
        return None

    return _mutate_period(
        paragraph,
        "termination period changed",
        "Changed a termination or notice period in a real CUAD paragraph.",
    )


def _mutate_liability_cap(paragraph: str) -> MutationResult | None:
    if not re.search(r"liability|liable|indemn", paragraph, re.IGNORECASE):
        return None

    amount_result = _mutate_amount(paragraph)

    if amount_result is not None:
        return MutationResult(
            mutation_type="liability cap changed",
            description="Changed a liability cap in a real CUAD paragraph.",
            original_text=amount_result.original_text,
            revised_text=amount_result.revised_text,
            expected_change=amount_result.expected_change,
        )

    return _mutate_period(
        paragraph,
        "liability cap changed",
        "Changed a liability limitation period in a real CUAD paragraph.",
    )


def _mutate_period(
    paragraph: str,
    mutation_type: str,
    description: str,
) -> MutationResult | None:
    match = re.search(
        r"\b\d{1,3}\s+(?:day|days|month|months|year|years)\b",
        paragraph,
        flags=re.IGNORECASE,
    )

    if match is None:
        for keyword in _PERIOD_KEYWORDS:
            if keyword in paragraph.casefold():
                revised = f"{paragraph} The applicable period is extended to 24 months."
                return _result(
                    mutation_type,
                    description,
                    paragraph,
                    revised,
                    "modified",
                    "extended to 24 months",
                )

        return None

    revised_value = "24 months"
    revised = _replace_first(paragraph, match.group(0), revised_value)
    return _result(
        mutation_type,
        description,
        paragraph,
        revised,
        "modified",
        revised_value,
    )


def _sentences(paragraph: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph)
        if sentence.strip()
    ]
