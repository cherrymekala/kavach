"""Case storage in Firestore. Falls back to memory when AUTH_DISABLED (local dev)."""

from ..config import get_settings
from ..models import Case

_memory: dict[str, Case] = {}


def _db():
    from google.cloud import firestore

    return firestore.Client(project=get_settings().gcp_project)


def _local() -> bool:
    return get_settings().auth_disabled


def save_case(case: Case) -> None:
    if _local():
        _memory[case.id] = case
        return
    _db().collection("cases").document(case.id).set(case.model_dump(mode="json"))


def load_case(case_id: str) -> Case | None:
    if _local():
        return _memory.get(case_id)
    snap = _db().collection("cases").document(case_id).get()
    return Case.model_validate(snap.to_dict()) if snap.exists else None


# Resolved cases stay in the daily scan until their documents are deleted.
OPEN = ("ready", "filed", "escalated", "resolved")


def open_cases() -> list[Case]:
    """Cases the daily tracker should look at (small volume, so no composite index needed)."""
    if _local():
        return [c for c in _memory.values() if c.status in OPEN]
    q = _db().collection("cases").where("status", "in", list(OPEN))
    return [Case.model_validate(s.to_dict()) for s in q.stream()]


def delete_case(case_id: str) -> None:
    if _local():
        _memory.pop(case_id, None)
        return
    _db().collection("cases").document(case_id).delete()
