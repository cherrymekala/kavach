from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from ..agents import escalation
from ..auth import current_user
from ..config import Settings, get_settings
from ..models import Case, FiledRequest, ReplyRequest
from ..tools import store

router = APIRouter(prefix="/tracker", tags=["tracker"])
case_router = APIRouter(prefix="/cases/{case_id}", tags=["tracker"])


def scheduler_only(
    request: Request,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """The service is public, so /tracker/tick must prove it is our Cloud Scheduler job."""
    if settings.auth_disabled:
        return
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token.")
    audience = f"https://{request.headers.get('host', '')}/tracker/tick"
    try:
        claims = id_token.verify_oauth2_token(
            authorization.removeprefix("Bearer "), google_requests.Request(), audience=audience
        )
    except ValueError as exc:
        raise HTTPException(401, "Invalid token.") from exc
    if claims.get("email") != f"kavach-scheduler@{settings.gcp_project}.iam.gserviceaccount.com":
        raise HTTPException(403, "Not the tracker scheduler.")


@router.post("/tick", dependencies=[Depends(scheduler_only)])
def tick() -> dict:
    """Called daily by Cloud Scheduler."""
    now = datetime.now(UTC)
    changed = 0
    for case in store.open_cases():
        if escalation.tick(case, now):
            store.save_case(case)
            changed += 1
    return {"changed": changed}


def _own(case_id: str, uid: str) -> Case:
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    return case


@case_router.post("/filed", response_model=Case)
def filed(case_id: str, body: FiledRequest, uid: str = Depends(current_user)) -> Case:
    """The patient sent the letter/complaint for a step; start that step's countdown."""
    case = escalation.mark_filed(_own(case_id, uid), body, datetime.now(UTC))
    store.save_case(case)
    return case


@case_router.post("/reply", response_model=Case)
def reply(case_id: str, body: ReplyRequest, uid: str = Depends(current_user)) -> Case:
    """The insurer (or dispute body) answered; resolve or move to the next step."""
    if body.outcome not in ("paid", "partly_paid", "rejected"):
        raise HTTPException(422, "outcome must be paid, partly_paid or rejected.")
    case = escalation.record_reply(_own(case_id, uid), body, datetime.now(UTC))
    store.save_case(case)
    return case
