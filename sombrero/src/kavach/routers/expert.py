"""Handoff to a human advocate (agents/expert.py): offer, consent, request.

GET  /cases/{id}/expert   whether to suggest it, what would be shared, whether already asked
POST /cases/{id}/expert   the patient consents and asks; goes to the triage queue (+ team email)
"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from ..agents import expert
from ..auth import current_user
from ..config import get_settings
from ..models import Case, CaseEvent, ExpertOffer, ExpertRequest, ExpertRequestBody
from ..tools import access, mail, store

log = logging.getLogger(__name__)
router = APIRouter(prefix="/cases/{case_id}/expert", tags=["expert"])


def _own(case_id: str, uid: str) -> Case:
    # The patient or a helper they invited (a caregiver or NGO often makes this call for them).
    return access.load(case_id, uid)


@router.get("", response_model=ExpertOffer)
def get_offer(case_id: str, uid: str = Depends(current_user)) -> ExpertOffer:
    case = _own(case_id, uid)
    return ExpertOffer(
        reason=expert.offer_reason(case),
        requested_at=case.expert_requested_at,
        shared=expert.SHARED,
    )


@router.post("", response_model=Case)
def request_expert(case_id: str, body: ExpertRequestBody, uid: str = Depends(current_user)) -> Case:
    case = _own(case_id, uid)
    if not body.consent:
        raise HTTPException(422, "Please agree to share the summary first.")
    phone = (body.phone or "").strip() or None
    email = (body.email or "").strip() or None
    if not phone and not (email and mail.EMAIL.match(email)):
        raise HTTPException(422, "Add a phone number or an email so the team can reach you.")
    if case.expert_requested_at:
        raise HTTPException(409, "You've already asked for an expert on this case.")

    now = datetime.now(UTC)
    reason = expert.offer_reason(case)
    summary = expert.summary(case)
    note = body.note.strip()[:2000]
    store.save_expert_request(
        ExpertRequest(
            id=uuid.uuid4().hex,
            case_id=case.id,
            owner=case.owner,
            created_at=now,
            country=case.country,
            reason=reason,
            summary=summary,
            phone=phone,
            email=email,
            note=note,
        )
    )
    team = get_settings().expert_team_email
    if team:
        try:  # best effort: the request is already safe in the queue
            mail.send(
                team,
                f"Expert request: {summary.get('insurer') or case.title or case.id}",
                expert.email_text(summary, phone, email, note, reason),
            )
        except Exception:
            log.warning("expert: emailing the team failed", exc_info=True)
    case.expert_requested_at = now
    case.events.append(
        CaseEvent(
            at=now,
            kind="expert_requested",
            text="You asked for a human expert. Our team will contact you to find the right advocate.",
        )
    )
    store.save_case(case)
    return case
