import asyncio
import json
from types import SimpleNamespace
from typing import Any, cast

import pytest
from starlette.responses import Response

from contract_diff.core.models.engine_result import EngineResult
from contract_diff.core.models.engine_status import EngineStatus
from contract_diff.rendering.models.rendered_document import RenderedDocument
from contract_diff_api.main import health
from contract_diff_api.routes import compare as compare_route
from contract_diff_api.routes.compare import (
    active_compare_engine_version,
    compare_documents,
    compare_documents_v2,
    engine_info,
)


class SuccessfulEngine:
    def __init__(self) -> None:
        self.original_pdf: bytes | None = None
        self.revised_pdf: bytes | None = None
        self.original_filename: str | None = None
        self.revised_filename: str | None = None

    def compare(
        self,
        original_pdf: bytes,
        revised_pdf: bytes,
        *_args: Any,
        **kwargs: Any,
    ) -> EngineResult:
        self.original_pdf = original_pdf
        self.revised_pdf = revised_pdf
        self.original_filename = str(kwargs["original_filename"])
        self.revised_filename = str(kwargs["revised_filename"])

        return EngineResult(
            status=EngineStatus.SUCCESS,
            rendered_document=RenderedDocument(
                filename="annotated.pdf",
                data=b"%PDF annotated",
            ),
        )


class RejectedEngine:
    def compare(self, *_args: Any, **_kwargs: Any) -> EngineResult:
        return EngineResult(
            status=EngineStatus.REJECTED,
            rendered_document=None,
            rejection_reason="LOW_DOCUMENT_SIMILARITY",
            message="The uploaded documents appear to be less than 50% similar.",
            similarity_score=42.7,
            warnings=("LOW_DOCUMENT_SIMILARITY",),
        )


class FailedEngine:
    def compare(self, *_args: Any, **_kwargs: Any) -> EngineResult:
        return EngineResult(
            status=EngineStatus.FAILED,
            message="Comparison failed.",
            warnings=("TEST_FAILURE",),
        )


def test_compare_success_returns_pdf_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTRACT_DIFF_COMPARE_ENGINE", "v1")

    response = call_compare(SuccessfulEngine())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        'attachment; filename="annotated.pdf"'
    )
    assert response.body == b"%PDF annotated"


def test_compare_rejected_returns_json_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTRACT_DIFF_COMPARE_ENGINE", "v1")

    response = call_compare(RejectedEngine())
    payload = json.loads(bytes(response.body))

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert payload == {
        "status": "rejected",
        "reason": "LOW_DOCUMENT_SIMILARITY",
        "message": "The uploaded documents appear to be less than 50% similar.",
        "similarity_score": 42.7,
        "warnings": ["LOW_DOCUMENT_SIMILARITY"],
    }


def test_compare_failed_returns_json_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTRACT_DIFF_COMPARE_ENGINE", "v1")

    response = call_compare(FailedEngine())
    payload = json.loads(bytes(response.body))

    assert response.status_code == 500
    assert payload == {
        "status": "failed",
        "reason": None,
        "message": "Comparison failed.",
        "similarity_score": None,
        "warnings": ["TEST_FAILURE"],
    }


def test_compare_reads_uploaded_files_and_passes_filenames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTRACT_DIFF_COMPARE_ENGINE", "v1")
    engine = SuccessfulEngine()

    response = call_compare(engine)

    assert response.status_code == 200
    assert engine.original_pdf == b"%PDF original"
    assert engine.revised_pdf == b"%PDF revised"
    assert engine.original_filename == "original.pdf"
    assert engine.revised_filename == "revised.pdf"


def test_health_endpoint_returns_ok() -> None:
    assert health() == {
        "status": "ok",
        "service": "contract-diff-engine",
        "version": "0.1.0",
    }


def test_compare_uses_v2_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CONTRACT_DIFF_COMPARE_ENGINE", raising=False)

    def fake_compare_v2(original_pdf: bytes, revised_pdf: bytes) -> tuple[bytes, Any]:
        assert original_pdf == b"%PDF original"
        assert revised_pdf == b"%PDF revised"
        return b"%PDF v2", fake_report()

    monkeypatch.setattr(compare_route, "compare_pdf_bytes_v2", fake_compare_v2)

    response = call_compare(FailedEngine())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.body == b"%PDF v2"


def test_compare_uses_v1_when_environment_selects_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTRACT_DIFF_COMPARE_ENGINE", "v1")
    engine = SuccessfulEngine()

    response = call_compare(engine)

    assert response.status_code == 200
    assert response.body == b"%PDF annotated"
    assert engine.original_pdf == b"%PDF original"


def test_compare_v2_route_returns_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        compare_route,
        "compare_pdf_bytes_v2",
        lambda _original, _revised: (b"%PDF direct v2", fake_report()),
    )

    response = asyncio.run(
        compare_documents_v2(
            original_file=cast(
                Any,
                UploadFileDouble("original.pdf", b"%PDF original"),
            ),
            revised_file=cast(
                Any,
                UploadFileDouble("revised.pdf", b"%PDF revised"),
            ),
        )
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.body == b"%PDF direct v2"


def test_invalid_engine_config_defaults_to_v2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTRACT_DIFF_COMPARE_ENGINE", "nonsense")

    monkeypatch.setattr(
        compare_route,
        "compare_pdf_bytes_v2",
        lambda _original, _revised: (b"%PDF fallback v2", fake_report()),
    )

    response = call_compare(FailedEngine())

    assert response.status_code == 200
    assert response.body == b"%PDF fallback v2"
    assert active_compare_engine_version() == "v2"


def test_engine_info_reports_active_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTRACT_DIFF_COMPARE_ENGINE", "v2")

    assert engine_info() == {"compare_engine": "v2"}


def call_compare(engine: object) -> Response:
    return asyncio.run(
        compare_documents(
            original_file=cast(
                Any,
                UploadFileDouble("original.pdf", b"%PDF original"),
            ),
            revised_file=cast(
                Any,
                UploadFileDouble("revised.pdf", b"%PDF revised"),
            ),
            engine=cast(Any, engine),
        )
    )


class UploadFileDouble:
    def __init__(self, filename: str, data: bytes) -> None:
        self.filename = filename
        self._data = data

    async def read(self) -> bytes:
        return self._data


def fake_report() -> Any:
    return SimpleNamespace(
        comparison_quality=SimpleNamespace(
            confidence=0.98,
            added_count=1,
            deleted_count=0,
            modified_count=0,
            uncertain_count=0,
        )
    )
