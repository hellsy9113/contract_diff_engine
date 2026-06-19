import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contract_diff_api.routes.compare import router as compare_router

DEFAULT_FRONTEND_ORIGINS = (
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
)
DEFAULT_FRONTEND_ORIGIN_REGEX = (
    r"https://.*\.(vercel\.app|netlify\.app|onrender\.com)"
)


def frontend_origins() -> list[str]:
    configured = os.getenv("FRONTEND_ORIGINS")

    if configured is None:
        return list(DEFAULT_FRONTEND_ORIGINS)

    origins = [
        origin.strip().rstrip("/")
        for origin in configured.split(",")
        if origin.strip()
    ]
    return origins or list(DEFAULT_FRONTEND_ORIGINS)


def frontend_origin_regex() -> str | None:
    configured = os.getenv("FRONTEND_ORIGIN_REGEX")

    if configured is None:
        return DEFAULT_FRONTEND_ORIGIN_REGEX

    configured = configured.strip()
    return configured or None


app = FastAPI(
    title="Contract Diff API",
    version="0.1.0",
)

app.include_router(compare_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "contract-diff-engine",
        "version": "0.1.0",
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins(),
    allow_origin_regex=frontend_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
