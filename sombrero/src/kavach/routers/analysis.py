from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ..agents.orchestrator import run_case
from ..auth import current_user
from ..config import get_settings
from ..models import CaseStatus
from ..tools import store

router = APIRouter(prefix="/cases/{case_id}", tags=["analysis"])

# A run writes `progress` at every step, so silence for this long means it is gone: the Cloud Run
# instance was recycled (CPU is throttled after the 202), or the pipeline died without writing a
# failure. Without this the case stayed "analysing" for ever and every retry got a 409.
STALE_ANALYSIS = 15 * 60


@router.post("/analyse", status_code=202)
def analyse(case_id: str, bg: BackgroundTasks, uid: str = Depends(current_user)) -> dict:
    """Start the agent pipeline. The UI watches the case document for progress."""
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    if case.status == CaseStatus.ANALYSING:
        age = store.seconds_since_update(case_id)
        if age is None or age < STALE_ANALYSIS:
            raise HTTPException(409, "The analysis is already running.")
        # Nothing has written progress for a quarter of an hour: the previous run is dead, so
        # take the case over rather than locking the patient out of their own case. If it somehow
        # still runs, it will write to the same document and be overwritten by this new attempt.
    if case.documents_deleted_at:
        raise HTTPException(410, "This case's documents were deleted after it was resolved.")
    if not case.documents:
        raise HTTPException(400, "Upload at least the rejection letter and the policy first.")
    limit = get_settings().analyses_per_day
    if not store.take_quota(f"analyse-{uid}-{datetime.now(UTC):%Y%m%d}", limit):
        raise HTTPException(
            429, f"You can run up to {limit} analyses a day. Please try again tomorrow."
        )
    case.status = CaseStatus.ANALYSING
    store.save_case(case)
    bg.add_task(run_case, case_id)
    return {"status": "started"}
