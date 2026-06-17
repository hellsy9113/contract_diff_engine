from fastapi import FastAPI

from contract_diff_api.routes.compare import router as compare_router

app = FastAPI(
    title="Contract Diff API",
    version="0.1.0",
)

app.include_router(compare_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
