import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import logs
from .config import get_settings
from .routers import (
    analysis,
    cases,
    documents,
    expert,
    filing,
    hearing,
    insights,
    mail,
    packs,
    payments,
    tracker,
    voice,
    voice_intake,
    whatsapp,
)

logs.setup()
log = logging.getLogger("kavach")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    asyncio.get_running_loop().set_exception_handler(logs.log_task_exception)
    yield


app = FastAPI(title="Kavach API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # HTTPExceptions are handled by FastAPI before this; anything here is a real bug.
    log.error("unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        {"detail": "Something went wrong on our side. Please try again."}, status_code=500
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(expert.router)
app.include_router(analysis.router)
app.include_router(filing.router)
app.include_router(hearing.router)
app.include_router(packs.router)
app.include_router(insights.router)
app.include_router(tracker.router)
app.include_router(tracker.case_router)
app.include_router(voice.router)
app.include_router(voice_intake.router)
app.include_router(whatsapp.router)
app.include_router(payments.router)
app.include_router(mail.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
