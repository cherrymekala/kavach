"""Helper mode: a patient shares their case with a caregiver, hospital desk or NGO.

POST   /cases/{id}/share            owner: a fresh one-time code (48 h); replaces any earlier one
DELETE /cases/{id}/helpers/{uid}    owner: remove a helper
POST   /share/redeem                helper: join a case with a code and their name
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import current_user
from ..models import Case, CaseEvent, Helper
from ..tools import store

router = APIRouter(tags=["sharing"])

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L: read aloud over the phone
CODE_LENGTH = 8  # ~40 bits; with single use, 48 h expiry and a daily redeem limit, not guessable
VALID_FOR = timedelta(hours=48)
MAX_HELPERS = 5
REDEEMS_PER_DAY = 10
INVALID = "This code is not valid or has expired. Ask the patient for a new one."


class ShareCode(BaseModel):
    code: str  # shown as XXXX-XXXX
    expires_at: datetime


class RedeemRequest(BaseModel):
    code: str
    name: str  # how the patient will see the helper, e.g. "Asha (Lotus Hospital billing)"


def _normalise(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def _hash(code: str) -> str:
    return hashlib.sha256(_normalise(code).encode()).hexdigest()


def _owned(case_id: str, uid: str) -> Case:
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    return case


@router.post("/cases/{case_id}/share", response_model=ShareCode)
def create_share_code(case_id: str, uid: str = Depends(current_user)) -> ShareCode:
    case = _owned(case_id, uid)
    if len(case.helpers) >= MAX_HELPERS:
        raise HTTPException(
            409, f"A case can have at most {MAX_HELPERS} helpers. Remove one first."
        )
    raw = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
    expires = datetime.now(UTC) + VALID_FOR
    if case.share_code_hash:
        store.delete_share_code(case.share_code_hash)  # only one live code per case
    case.share_code_hash = _hash(raw)
    store.save_share_code(
        case.share_code_hash, {"case_id": case.id, "expires_at": expires.isoformat()}
    )
    store.save_case(case)
    return ShareCode(code=f"{raw[:4]}-{raw[4:]}", expires_at=expires)


@router.delete("/cases/{case_id}/helpers/{helper_uid}", response_model=Case)
def remove_helper(case_id: str, helper_uid: str, uid: str = Depends(current_user)) -> Case:
    case = _owned(case_id, uid)
    helper = next((h for h in case.helpers if h.uid == helper_uid), None)
    if not helper:
        raise HTTPException(404, "That helper is not on this case.")
    case.helpers = [h for h in case.helpers if h.uid != helper_uid]
    case.helper_ids = [h.uid for h in case.helpers]
    case.events.append(
        CaseEvent(
            at=datetime.now(UTC),
            kind="helper_removed",
            text=f"{helper.name} can no longer see this case.",
        )
    )
    store.save_case(case)
    return case


@router.post("/share/redeem", response_model=Case)
def redeem_share_code(body: RedeemRequest, uid: str = Depends(current_user)) -> Case:
    name = " ".join(body.name.split())[:80]
    if not name:
        raise HTTPException(422, "Please add your name, so the patient knows who is helping.")
    if not store.take_quota(f"redeem:{uid}:{datetime.now(UTC):%Y-%m-%d}", REDEEMS_PER_DAY):
        raise HTTPException(429, "Too many tries today. Please try again tomorrow.")
    code_hash = _hash(body.code)
    entry = store.load_share_code(code_hash)
    if not entry or datetime.fromisoformat(entry["expires_at"]) < datetime.now(UTC):
        raise HTTPException(404, INVALID)
    case = store.load_case(entry["case_id"])
    if not case or case.share_code_hash != code_hash:
        raise HTTPException(404, INVALID)
    if case.owner == uid:
        raise HTTPException(409, "This is your own case. Send the code to the person helping you.")
    if uid not in case.helper_ids:
        if len(case.helpers) >= MAX_HELPERS:
            raise HTTPException(409, f"This case already has {MAX_HELPERS} helpers.")
        now = datetime.now(UTC)
        case.helpers.append(Helper(uid=uid, name=name, added_at=now))
        case.helper_ids = [h.uid for h in case.helpers]
        case.events.append(
            CaseEvent(at=now, kind="helper_added", text=f"{name} can now help with this case.")
        )
    # Single use: the code is spent once someone joins with it.
    store.delete_share_code(code_hash)
    case.share_code_hash = None
    store.save_case(case)
    return case
