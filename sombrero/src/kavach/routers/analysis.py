from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ..agents.orchestrator import run_case
from ..auth import current_user
from ..models import CaseStatus
from ..tools import store

router = APIRouter(prefix="/cases/{case_id}", tags=["analysis"])


@router.post("/analyse", status_code=202)
def analyse(case_id: str, bg: BackgroundTasks, uid: str = Depends(current_user)) -> dict:
    """Start the agent pipeline. The UI watches the case document for progress."""
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    if case.status == CaseStatus.ANALYSING:
        raise HTTPException(409, "The analysis is already running.")
    if not case.documents:
        raise HTTPException(400, "Upload at least the rejection letter and the policy first.")
    case.status = CaseStatus.ANALYSING
    store.save_case(case)
    bg.add_task(run_case, case_id)
    return {"status": "started"}
