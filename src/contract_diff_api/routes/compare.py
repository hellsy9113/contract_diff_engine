import logging
import os
from typing import Literal, cast

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse, Response

from contract_diff.core.models.engine_result import EngineResult
from contract_diff.core.models.engine_status import EngineStatus
from contract_diff.core.services.contract_diff_engine import ContractDiffEngine
from contract_diff.services.compare_v2 import compare_pdf_bytes_v2
from contract_diff_api.schemas.error_response import ErrorResponse
from contract_diff_api.services.engine_factory import get_engine

logger = logging.getLogger(__name__)
router = APIRouter()
CompareEngineVersion = Literal["v1", "v2"]


@router.post(
    "/compare",
    responses={
        200: {"content": {"application/pdf": {}}},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def compare_documents(
    original_file: UploadFile = File(...),
    revised_file: UploadFile = File(...),
    engine: ContractDiffEngine = Depends(get_engine),
) -> Response:
    original_pdf = await original_file.read()
    revised_pdf = await revised_file.read()

    logger.debug("original bytes: %s", len(original_pdf))
    logger.debug("revised bytes: %s", len(revised_pdf))

    if active_compare_engine_version() == "v2":
        return _compare_v2_response(original_pdf, revised_pdf)

    result = engine.compare(
        original_pdf,
        revised_pdf,
        original_filename=original_file.filename or "original.pdf",
        revised_filename=revised_file.filename or "revised.pdf",
    )

    return _response_for_result(result)


@router.post(
    "/compare-v2",
    responses={
        200: {"content": {"application/pdf": {}}},
        500: {"model": ErrorResponse},
    },
)
async def compare_documents_v2(
    original_file: UploadFile = File(...),
    revised_file: UploadFile = File(...),
) -> Response:
    original_pdf = await original_file.read()
    revised_pdf = await revised_file.read()
    return _compare_v2_response(original_pdf, revised_pdf)


@router.get("/engine/info")
def engine_info() -> dict[str, str]:
    return {"compare_engine": active_compare_engine_version()}


def active_compare_engine_version() -> CompareEngineVersion:
    configured = os.getenv("CONTRACT_DIFF_COMPARE_ENGINE", "v2").strip().casefold()

    if configured in {"v1", "v2"}:
        return cast(CompareEngineVersion, configured)

    logger.warning(
        "Invalid CONTRACT_DIFF_COMPARE_ENGINE=%r; defaulting to v2",
        configured,
    )
    return "v2"


def _compare_v2_response(original_pdf: bytes, revised_pdf: bytes) -> Response:
    output_pdf, report = compare_pdf_bytes_v2(original_pdf, revised_pdf)
    logger.info(
        "compare v2 result: confidence=%s added=%s deleted=%s modified=%s "
        "uncertain=%s",
        report.comparison_quality.confidence,
        report.comparison_quality.added_count,
        report.comparison_quality.deleted_count,
        report.comparison_quality.modified_count,
        report.comparison_quality.uncertain_count,
    )
    return Response(
        content=output_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="annotated-v2.pdf"'},
    )


def _response_for_result(result: EngineResult) -> Response:
    if (
        result.status is EngineStatus.SUCCESS
        and result.rendered_document is not None
    ):
        return Response(
            content=result.rendered_document.data,
            media_type=result.rendered_document.content_type,
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{result.rendered_document.filename}"'
                )
            },
        )

    if result.status is EngineStatus.REJECTED:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse.from_engine_result(result).model_dump(
                mode="json"
            ),
        )

    return JSONResponse(
        status_code=500,
        content=ErrorResponse.from_engine_result(result).model_dump(mode="json"),
    )
