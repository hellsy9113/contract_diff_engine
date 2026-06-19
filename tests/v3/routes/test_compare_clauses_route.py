import asyncio
from typing import Any, cast

import pytest
from fastapi import HTTPException

from contract_diff.v3.models import V3ClauseCompareResponse, V3CompareSummary
from contract_diff.v3.routes import compare_clauses as compare_clauses_route
from contract_diff.v3.routes.compare_clauses import compare_clauses_route as endpoint


def test_v3_route_returns_json_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        compare_clauses_route,
        "compare_clauses_v3",
        lambda *_args, **kwargs: V3ClauseCompareResponse(
            summary=V3CompareSummary(
                total_clauses=0,
                unchanged_clauses=0,
                changed_clauses=0,
                added_clauses=0,
                deleted_clauses=0,
                modified_clauses=0,
            ),
            clauses=[],
            debug=None if not kwargs.get("debug") else None,
        ),
    )

    response = asyncio.run(
        endpoint(
            original=cast(Any, UploadFileDouble("original.pdf", b"%PDF original")),
            revised=cast(Any, UploadFileDouble("revised.pdf", b"%PDF revised")),
            debug=False,
        )
    )

    assert response.version == "v3"
    assert response.summary.total_clauses == 0


def test_v3_route_rejects_invalid_pdf_upload() -> None:
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(
            endpoint(
                original=cast(Any, UploadFileDouble("original.txt", b"not a pdf")),
                revised=cast(Any, UploadFileDouble("revised.pdf", b"%PDF revised")),
                debug=False,
            )
        )

    assert excinfo.value.status_code == 422
    assert "not a valid PDF" in str(excinfo.value.detail)


def test_v3_route_passes_debug_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_compare(
        original_file: bytes,
        revised_file: bytes,
        *,
        original_filename: str | None,
        revised_filename: str | None,
        debug: bool,
    ) -> V3ClauseCompareResponse:
        captured["original"] = original_file
        captured["revised"] = revised_file
        captured["original_filename"] = original_filename
        captured["revised_filename"] = revised_filename
        captured["debug"] = debug
        return V3ClauseCompareResponse(
            summary=V3CompareSummary(
                total_clauses=0,
                unchanged_clauses=0,
                changed_clauses=0,
                added_clauses=0,
                deleted_clauses=0,
                modified_clauses=0,
            ),
            clauses=[],
        )

    monkeypatch.setattr(compare_clauses_route, "compare_clauses_v3", fake_compare)

    asyncio.run(
        endpoint(
            original=cast(Any, UploadFileDouble("original.pdf", b"%PDF original")),
            revised=cast(Any, UploadFileDouble("revised.pdf", b"%PDF revised")),
            debug=True,
        )
    )

    assert captured == {
        "original": b"%PDF original",
        "revised": b"%PDF revised",
        "original_filename": "original.pdf",
        "revised_filename": "revised.pdf",
        "debug": True,
    }


class UploadFileDouble:
    def __init__(self, filename: str, data: bytes) -> None:
        self.filename = filename
        self._data = data

    async def read(self) -> bytes:
        return self._data
