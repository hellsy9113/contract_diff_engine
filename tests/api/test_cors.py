from __future__ import annotations

import asyncio
from typing import Any

import pytest
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from contract_diff_api.main import (
    frontend_origin_regex,
    frontend_origins,
)


def test_frontend_origins_are_parsed_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FRONTEND_ORIGINS",
        " https://app.example.com/ , http://localhost:3000 ",
    )

    assert frontend_origins() == [
        "https://app.example.com",
        "http://localhost:3000",
    ]


def test_empty_frontend_origin_regex_disables_regex(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FRONTEND_ORIGIN_REGEX", "")

    assert frontend_origin_regex() is None


def test_default_cors_allows_common_deployment_frontend_origin() -> None:
    response = asyncio.run(
        call_app(
            cors_app(),
            method="GET",
            path="/health",
            headers={
                "origin": "https://contract-diff-ui.vercel.app",
            },
        )
    )

    assert response["status"] == 200
    headers = response["headers"]
    assert (
        headers["access-control-allow-origin"] == "https://contract-diff-ui.vercel.app"
    )
    assert headers["access-control-allow-credentials"] == "true"
    assert "Content-Disposition" in headers["access-control-expose-headers"]


def test_cors_preflight_allows_compare_post_from_render_frontend() -> None:
    response = asyncio.run(
        call_app(
            cors_app(),
            method="OPTIONS",
            path="/compare",
            headers={
                "origin": "https://contract-diff-frontend.onrender.com",
                "access-control-request-method": "POST",
            },
        )
    )

    assert response["status"] == 200
    headers = response["headers"]
    assert (
        headers["access-control-allow-origin"]
        == "https://contract-diff-frontend.onrender.com"
    )
    assert "POST" in headers["access-control-allow-methods"]


def cors_app() -> ASGIApp:
    return CORSMiddleware(
        ok_app,
        allow_origins=frontend_origins(),
        allow_origin_regex=frontend_origin_regex(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )


async def ok_app(_scope: Scope, _receive: Receive, send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": b"{}"})


async def call_app(
    asgi_app: ASGIApp,
    *,
    method: str,
    path: str,
    headers: dict[str, str],
) -> dict[str, Any]:
    messages: list[Message] = []
    sent_request = False

    async def receive() -> Message:
        nonlocal sent_request

        if sent_request:
            return {"type": "http.disconnect"}

        sent_request = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        messages.append(message)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": [
            (name.lower().encode("latin-1"), value.encode("latin-1"))
            for name, value in headers.items()
        ],
        "client": ("testclient", 50000),
        "server": ("testserver", 443),
    }

    await asgi_app(scope, receive, send)
    response_start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    response_headers = {
        name.decode("latin-1"): value.decode("latin-1")
        for name, value in response_start["headers"]
    }
    return {"status": response_start["status"], "headers": response_headers}
