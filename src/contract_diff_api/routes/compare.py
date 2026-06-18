import logging

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse, Response

from contract_diff.core.models.engine_result import EngineResult
from contract_diff.core.models.engine_status import EngineStatus
from contract_diff.core.services.contract_diff_engine import ContractDiffEngine
from contract_diff_api.schemas.error_response import ErrorResponse
from contract_diff_api.services.engine_factory import get_engine

logger = logging.getLogger(__name__)
router = APIRouter()


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

    result = engine.compare(
        original_pdf,
        revised_pdf,
        original_filename=original_file.filename or "original.pdf",
        revised_filename=revised_file.filename or "revised.pdf",
    )

    return _response_for_result(result)


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
