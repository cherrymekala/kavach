from fastapi import FastAPI

from .routers import analysis, cases, documents, tracker

app = FastAPI(title="Kavach API", version="0.1.0")
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(analysis.router)
app.include_router(tracker.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
