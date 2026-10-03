from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import analysis, cases, documents, filing, hearing, tracker

app = FastAPI(title="Kavach API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(analysis.router)
app.include_router(filing.router)
app.include_router(hearing.router)
app.include_router(tracker.router)
app.include_router(tracker.case_router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
