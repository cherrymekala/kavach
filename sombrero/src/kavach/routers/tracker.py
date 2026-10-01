from fastapi import APIRouter

from ..agents.escalation import advance_overdue_cases

router = APIRouter(prefix="/tracker", tags=["tracker"])


@router.post("/tick")
def tick() -> dict:
    """Called daily by Cloud Scheduler (OIDC-authenticated in production)."""
    return {"advanced": advance_overdue_cases()}
