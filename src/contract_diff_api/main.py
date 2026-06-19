import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contract_diff_api.routes.compare import router as compare_router

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


frontend_origins = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://localhost:3001",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in frontend_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)