from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from contract_diff.extraction.enums.document_format import DocumentFormat
from contract_diff.extraction.exceptions.extraction import InvalidDocumentError
from contract_diff.extraction.identification.format_detector import FormatDetector
from contract_diff.v3.comparison.clause_compare_service import compare_clauses_v3
from contract_diff.v3.models import V3ClauseCompareResponse

router = APIRouter(prefix="/v3", tags=["v3"])


@router.post("/compare/clauses", response_model=V3ClauseCompareResponse)
async def compare_clauses_route(
    original: UploadFile | None = File(None),
    revised: UploadFile | None = File(None),
    original_file: UploadFile | None = File(None),
    revised_file: UploadFile | None = File(None),
    debug: bool = Query(False),
) -> V3ClauseCompareResponse | JSONResponse:
    resolved_original, resolved_revised = _resolve_uploads(
        original=original,
        revised=revised,
        original_file=original_file,
        revised_file=revised_file,
    )

    original_bytes = await resolved_original.read()
    revised_bytes = await resolved_revised.read()

    _validate_pdf_upload(
        original_bytes,
        resolved_original.filename,
        field_name="original",
    )
    _validate_pdf_upload(
        revised_bytes,
        resolved_revised.filename,
        field_name="revised",
    )

    try:
        return compare_clauses_v3(
            original_bytes,
            revised_bytes,
            original_filename=resolved_original.filename or "original.pdf",
            revised_filename=resolved_revised.filename or "revised.pdf",
            debug=debug,
        )
    except InvalidDocumentError as exc:
        return JSONResponse(
            status_code=422,
            content={"message": str(exc)},
        )


def _resolve_uploads(
    *,
    original: UploadFile | None,
    revised: UploadFile | None,
    original_file: UploadFile | None,
    revised_file: UploadFile | None,
) -> tuple[UploadFile, UploadFile]:
    resolved_original = original or original_file
    resolved_revised = revised or revised_file

    if resolved_original is None or resolved_revised is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Both original and revised PDF files are required. "
                "Accepted field names: original/revised or original_file/revised_file."
            ),
        )

    return resolved_original, resolved_revised


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
