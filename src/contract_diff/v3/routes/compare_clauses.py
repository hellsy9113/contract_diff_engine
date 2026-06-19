from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.extraction.exceptions.extraction import InvalidDocumentError
from contract_diff.extraction.identification.format_detector import FormatDetector
from contract_diff.v3.comparison.clause_compare_service import compare_clauses_v3
from contract_diff.v3.models import V3ClauseCompareResponse

router = APIRouter(prefix="/v3", tags=["v3"])


@router.post("/compare/clauses", response_model=V3ClauseCompareResponse)
async def compare_clauses_route(
    original: UploadFile = File(...),
    revised: UploadFile = File(...),
    debug: bool = Query(False),
) -> V3ClauseCompareResponse:
    original_bytes = await original.read()
    revised_bytes = await revised.read()

    _validate_pdf_upload(original_bytes, original.filename, field_name="original")
    _validate_pdf_upload(revised_bytes, revised.filename, field_name="revised")

    try:
        return compare_clauses_v3(
            original_bytes,
            revised_bytes,
            original_filename=original.filename or "original.pdf",
            revised_filename=revised.filename or "revised.pdf",
            debug=debug,
        )
    except InvalidDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _validate_pdf_upload(
    file_bytes: bytes,
    filename: str | None,
    *,
    field_name: str,
) -> None:
    if not file_bytes:
        raise HTTPException(
            status_code=422,
            detail=f"The {field_name} upload is empty.",
        )

    detected = FormatDetector.detect(BytesIO(file_bytes))

    if detected is not DocumentFormat.PDF:
        upload_name = filename or f"{field_name}.pdf"
        raise HTTPException(
            status_code=422,
            detail=f"{upload_name} is not a valid PDF upload.",
        )
