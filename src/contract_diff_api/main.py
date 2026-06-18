from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contract_diff_api.routes.compare import router as compare_router

app = FastAPI(
    title="Contract Diff API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compare_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}