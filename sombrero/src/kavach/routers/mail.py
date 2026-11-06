"""Send the appeal by email and log the insurer's replies on the tracker.

GET  /cases/{id}/send-appeal   what would be sent, and what is still missing
POST /cases/{id}/send-appeal   email the letter to the insurer and start the reply deadline
POST /mail/inbound?token=...   Postmark's inbound webhook for replies to case addresses
"""

import base64
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..agents import appeal_mail, escalation, filing
from ..auth import current_user
from ..models import Case, CaseEvent, Document, FiledRequest
from ..tools import files, mail, packs, payments, store
from . import whatsapp
from .documents import ALLOWED, MAX_BYTES, MAX_DOCUMENTS, safe_name

log = logging.getLogger(__name__)
router = APIRouter(tags=["mail"])

INSURER_STEP = 0  # only the first rung (the insurer's own grievance cell) is an email


class SendAppealRequest(BaseModel):
    to: str


class AppealMail(BaseModel):
    to: str | None  # the insurer's grievance email: remembered, or from the pack's directory
    to_source: str | None  # where `to` came from: "case" | "directory" | None
    cc: str | None  # the patient, so they hold a copy
    reply_to: str | None  # this case's own address; None when inbound mail is not set up
    subject: str | None
    attachments: list[str]
    missing: list[str]  # name | email | letter | letter_blanks | step | already_sent
    blanks: list[str]
    sent_on: datetime | None
    dry_run: bool


def _own(case_id: str, uid: str) -> Case:
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    return case


def _sent_event(case: Case) -> CaseEvent | None:
    return next((e for e in case.events if e.kind == "emailed" and e.step == INSURER_STEP), None)


def _attachments(case: Case) -> list[tuple[str, bytes, str]]:
    out = [("appeal-letter.pdf", filing.render_letter_pdf(case.letter), "application/pdf")]
    if case.letter.local:
        out.append(
            (
                f"appeal-letter-{case.letter.language}.pdf",
                filing.render_letter_pdf(case.letter, True),
                "application/pdf",
            )
        )
    return out


def _preview(case: Case) -> AppealMail:
    who = case.complainant
    contact = packs.insurer_contact(case.country, case.facts.insurer if case.facts else None)
    to, source = (who.insurer_email, "case") if who and who.insurer_email else (None, None)
    if not to and contact:
        to, source = contact.get("email"), "directory"
    gaps = appeal_mail.blanks(case.letter.english) if case.letter else []
    sent = _sent_event(case)
    missing = [
        code
        for code, gap in [
            ("letter", not case.letter),
            ("letter_blanks", bool(gaps)),
            ("name", not (who and who.name)),
            ("email", not (who and who.email)),
            ("step", case.escalation_step != INSURER_STEP),
            ("already_sent", sent is not None),
        ]
        if gap
    ]
    names = ["appeal-letter.pdf"] + (
        [f"appeal-letter-{case.letter.language}.pdf"] if case.letter and case.letter.local else []
    )
    return AppealMail(
        to=to,
        to_source=source,
        cc=who.email if who else None,
        reply_to=mail.reply_address(case.id),
        subject=case.letter.subject if case.letter else None,
        attachments=names if case.letter else [],
        missing=missing,
        blanks=gaps,
        sent_on=sent.at if sent else None,
        dry_run=not mail.configured(),
    )


@router.get("/cases/{case_id}/send-appeal", response_model=AppealMail)
def appeal_preview(case_id: str, uid: str = Depends(current_user)) -> AppealMail:
    return _preview(_own(case_id, uid))


@router.post("/cases/{case_id}/send-appeal", response_model=Case)
def send_appeal(case_id: str, body: SendAppealRequest, uid: str = Depends(current_user)) -> Case:
    case = _own(case_id, uid)
    if not payments.is_unlocked(case):
        raise HTTPException(402, "Unlock the appeal pack to send it.")
    preview = _preview(case)
    messages = {
        "letter": "There is no appeal letter yet.",
        "letter_blanks": "Fill in the blanks in your letter first: " + ", ".join(preview.blanks),
        "name": "Add your name in the filing details first.",
        "email": "Add your email in the filing details, so you get a copy and the replies.",
        "step": "Your case has moved past the insurer step; file the next step instead.",
        "already_sent": "Your appeal was already emailed to the insurer.",
    }
    for code in preview.missing:
        raise HTTPException(409, messages[code])
    to = body.to.strip()
    if not mail.EMAIL.match(to):
        raise HTTPException(422, "That doesn't look like an email address.")

    subject, text = appeal_mail.compose(case, preview.reply_to)
    try:
        mail.send(
            to,
            subject,
            text,
            cc=preview.cc,
            reply_to=preview.reply_to,
            attachments=_attachments(case),
        )
    except mail.MailError as exc:
        raise HTTPException(502, str(exc)) from exc

    now = datetime.now(UTC)
    case.complainant.insurer_email = to
    case.events.append(
        CaseEvent(
            at=now,
            kind="emailed",
            text=f"Appeal emailed to {to}. Their reply will appear here.",
            step=INSURER_STEP,
        )
    )
    # Sending is filing: the insurer's reply clock starts today.
    escalation.mark_filed(case, FiledRequest(filed_on=now.date(), step=INSURER_STEP), now)
    store.save_case(case)
    return case


def _save_attachments(case: Case, attachments: list[dict]) -> int:
    saved = 0
    for att in attachments or []:
        name = safe_name(att.get("Name"))
        if Path(name).suffix.lower() not in ALLOWED or len(case.documents) >= MAX_DOCUMENTS:
            continue
        try:
            data = base64.b64decode(att.get("Content") or "", validate=True)
        except ValueError:
            continue
        if not data or len(data) > MAX_BYTES:
            continue
        doc_id = uuid.uuid4().hex
        uri = files.put(f"{case.id}/{doc_id}-insurer-{name}", data, att.get("ContentType"))
        case.documents.append(
            Document(
                id=doc_id, filename=f"insurer-{name}", gcs_uri=uri, uploaded_at=datetime.now(UTC)
            )
        )
        saved += 1
    return saved


@router.post("/mail/inbound")
async def inbound(request: Request, token: str | None = None) -> dict:
    """Postmark inbound webhook. Always 200 for mail we can't place, so Postmark won't retry it."""
    if not mail.token_ok(token):
        raise HTTPException(403, "Not the mail service.")
    msg = await request.json()
    recipients = [r.get("Email", "") for r in (msg.get("ToFull") or []) + (msg.get("CcFull") or [])]
    recipients += [msg.get("OriginalRecipient", ""), msg.get("To", "")]
    case_id = mail.case_for_addresses(recipients)
    case = store.load_case(case_id) if case_id else None
    if not case:
        log.info("mail: inbound message for no known case")
        return {"ok": True, "matched": False}

    sender = (msg.get("FromFull") or {}).get("Email") or msg.get("From", "the insurer")
    subject = (msg.get("Subject") or "").strip()[:200]
    text = (msg.get("StrippedTextReply") or msg.get("TextBody") or "").strip()[:8000]
    attachments = msg.get("Attachments") or []
    read = appeal_mail.read_reply(subject, text)
    saved = 0 if case.documents_deleted_at else _save_attachments(case, attachments)

    summary = f" {read.summary}" if read else ""
    files_note = f" {saved} attachment(s) added to your files." if saved else ""
    event = CaseEvent(
        at=datetime.now(UTC),
        kind="insurer_reply",
        text=f"{sender} replied by email: “{subject}”.{summary}{files_note} Tell us what they decided.",
        step=case.escalation_step,
    )
    case.events.append(event)
    store.save_case(case)

    # Best effort: the reply is already safe on the case.
    who = case.complainant
    if who and who.email:
        try:
            mail.send(
                who.email,
                f"Your insurer replied: {subject}",
                "Your insurer replied to your appeal. Kavach logged it on your case tracker; "
                "open the app to record what they decided.\n\n--- Their message ---\n" + text,
                attachments=[
                    (
                        a.get("Name", "attachment"),
                        base64.b64decode(a.get("Content") or ""),
                        a.get("ContentType", ""),
                    )
                    for a in attachments
                ][:5],
            )
        except Exception:
            log.warning("mail: forwarding the reply to the patient failed", exc_info=True)
    try:
        whatsapp.notify_case(case, event.text)
    except Exception:
        log.warning("whatsapp: reply notice failed", exc_info=True)
    return {"ok": True, "matched": True}
