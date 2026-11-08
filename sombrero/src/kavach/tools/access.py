"""Who may work on a case: the patient who owns it, and helpers they invited with a share code.

Helpers can do everything needed to fight the claim (upload, analyse, letter, filing, email,
tracker, hearing). Deleting the case and managing who it is shared with stay with the owner.
"""

from fastapi import HTTPException

from ..models import Case
from . import store


def can_work_on(case: Case | None, uid: str) -> bool:
    return bool(case) and (case.owner == uid or uid in case.helper_ids)


def load(case_id: str, uid: str) -> Case:
    """The case, if this user may work on it; otherwise 404 (never reveal that it exists)."""
    case = store.load_case(case_id)
    if not can_work_on(case, uid):
        raise HTTPException(404, "Case not found.")
    return case
