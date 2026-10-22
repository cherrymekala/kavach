"""Case storage in Firestore. Falls back to memory when AUTH_DISABLED (local dev)."""

from datetime import UTC, datetime, timedelta

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


def seconds_since_update(case_id: str) -> float | None:
    """Age of the case document's last write, or None when it cannot be known.

    Firestore stamps every write, and the pipeline writes `progress` as it goes, so during an
    analysis this is the age of the last sign of life — which is exactly what a stale-run check
    needs. Local mode keeps cases in memory with no metadata, hence None.
    """
    if _local():
        return None
    snap = _db().collection("cases").document(case_id).get()
    if not snap.exists:
        return None
    updated = getattr(snap, "update_time", None)
    return (datetime.now(UTC) - updated).total_seconds() if updated else None


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


def list_cases(owner: str) -> list[Case]:
    """Newest first. Equality filter only, so no composite index is needed; sorted here."""
    if _local():
        cases = [c for c in _memory.values() if c.owner == owner]
    else:
        query = _db().collection("cases").where("owner", "==", owner)
        cases = [Case.model_validate(s.to_dict()) for s in query.stream()]
    return sorted(
        cases, key=lambda c: c.created_at.isoformat() if c.created_at else "", reverse=True
    )


_quota: dict[str, int] = {}


def take_quota(key: str, limit: int) -> bool:
    """Atomically count one use of `key`; False once `limit` is reached."""
    if _local():
        if _quota.get(key, 0) >= limit:
            return False
        _quota[key] = _quota.get(key, 0) + 1
        return True
    from google.cloud import firestore

    db = _db()
    ref = db.collection("quotas").document(key)

    @firestore.transactional
    def bump(tx) -> bool:
        used = (ref.get(transaction=tx).to_dict() or {}).get("used", 0)
        if used >= limit:
            return False
        tx.set(ref, {"used": used + 1})
        return True

    return bump(db.transaction())


# ── Channel sessions (WhatsApp). One small document per phone number. ─────────────────

_sessions: dict[str, dict] = {}
_seen: set[str] = set()


def _session_key(channel: str, key: str) -> str:
    return f"{channel}:{key}"


def load_session(channel: str, key: str) -> dict:
    """Conversation state for one person on one channel. Empty dict when new."""
    if _local():
        return dict(_sessions.get(_session_key(channel, key), {}))
    snap = _db().collection("sessions").document(_session_key(channel, key)).get()
    return (snap.to_dict() or {}) if snap.exists else {}


def save_session(channel: str, key: str, data: dict) -> None:
    if _local():
        _sessions[_session_key(channel, key)] = dict(data)
        return
    _db().collection("sessions").document(_session_key(channel, key)).set(dict(data))


def sessions_for(uid: str) -> list[tuple[str, dict]]:
    """Every channel session owned by `uid`, as (key, data).

    Only one equality filter, so no Firestore composite index is needed; the channel is
    filtered here.
    """
    if _local():
        items = list(_sessions.items())
    else:
        items = [
            (s.id, s.to_dict() or {})
            for s in _db().collection("sessions").where("uid", "==", uid).stream()
        ]
    out = []
    for doc_id, data in items:
        channel, _, key = doc_id.partition(":")
        if channel == "whatsapp" and key:
            out.append((key, data))
    return out


def claim_once(key: str) -> bool:
    """True the first time `key` is seen.

    Meta redelivers a webhook whenever it doesn't get a fast 200, so without this the patient
    would get the same reply twice (and the analysis quota would be spent twice).

    Meta's retries are minutes apart, so the marker only has to outlive them: `expire_at` is a
    week out and a Firestore TTL policy (triangulum/main.tf) clears the collection for us.
    """
    if _local():
        if key in _seen:
            return False
        _seen.add(key)
        return True
    from google.api_core import exceptions as gexc

    now = datetime.now(UTC)
    ref = _db().collection("seen").document(key)
    try:
        # Firestore TTL deletes a document once the timestamp in the TTL field is in the past,
        # so the field must be an expiry, not the insertion time.
        ref.create({"at": now, "expire_at": now + timedelta(days=7)})
        return True
    except (gexc.AlreadyExists, gexc.Conflict):
        return False
