"""WhatsApp channel over Meta's Cloud API.

Inbound
  GET  /whatsapp/webhook   answers Meta's subscription challenge.
  POST /whatsapp/webhook   receives messages. The raw body is signed with the app secret
                           (X-Hub-Signature-256); we verify it, acknowledge immediately and do
                           the work in a background task, because Meta retries anything slow or
                           non-200 and a retry means the patient gets a duplicate reply.

Outbound
  Free-form replies inside Meta's 24-hour window, and a pre-approved template outside it, so a
  deadline reminder still arrives a week later (`tools/whatsapp.py`).

Who is talking
  The number itself identifies the patient, exactly like the Twilio phone line: sign-in is
  Firebase phone OTP, so `tools/accounts.py` turns the sender into a uid and their cases, with
  no linking step and no second password. A patient who sends a photo of the rejection letter
  gets a case created for them, in the country their dialling code implies.

Media, quota and erasure all reuse the web path — same allow-list, same 20 MB ceiling, the same
per-day analysis budget (so WhatsApp can't be used to spend past the web cap) and the same
`DELETE` promise.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response

from ..agents import assistant, escalation, filing
from ..agents import whatsapp as copy
from ..agents.orchestrator import run_case
from ..config import get_settings
from ..models import (
    Case,
    CaseEvent,
    CaseKind,
    CaseStatus,
    Document,
    FiledRequest,
    ReplyRequest,
)
from ..tools import accounts, files, payments, store
from ..tools import whatsapp as wa
from ..tools.money import money
from . import documents as uploads

log = logging.getLogger("kavach.whatsapp")

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

CHANNEL = "whatsapp"
# Images arrive with a MIME type but usually no filename, so we name them from the type.
IMAGE_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _mask(phone: str) -> str:
    """Logs are operationally useful with the last few digits only, and nothing more."""
    return f"…{phone[-4:]}" if len(phone) > 4 else "…"


# ── Webhook ───────────────────────────────────────────────────────────────────────────


@router.get("/webhook")
def verify(request: Request) -> Response:
    """Meta's subscription handshake: echo hub.challenge when the verify token matches."""
    answer = wa.challenge(dict(request.query_params))
    if answer is None:
        raise HTTPException(403, "Bad verify token.")
    return Response(answer, media_type="text/plain")


@router.post("/webhook")
async def receive(request: Request, bg: BackgroundTasks) -> dict:
    body = await request.body()
    if not wa.signature_ok(body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(403, "Bad signature.")
    try:
        payload = json.loads(body or b"{}")
    except ValueError as exc:
        raise HTTPException(400, "Malformed JSON.") from exc
    bg.add_task(handle, payload)
    return {"status": "received"}


def handle(payload: dict) -> None:
    """Walk Meta's envelope and answer each message. One bad message never stops the rest."""
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            for msg in value.get("messages") or []:
                try:
                    _message(msg)
                except Exception:
                    log.exception("whatsapp: failed on message %s", msg.get("id"))


def _message(msg: dict) -> None:
    sender = str(msg.get("from") or "")
    if not sender:
        return
    message_id = str(msg.get("id") or "")
    if message_id and not store.claim_once(f"wa-{message_id}"):
        log.info("whatsapp: ignoring redelivered message %s", message_id)
        return

    if message_id:
        _read(message_id)

    session = store.load_session(CHANNEL, sender)
    session.update({"channel": CHANNEL, "last_in_at": datetime.now(UTC)})

    uid = accounts.uid_for_phone(sender)
    if not uid:
        _say(sender, copy.ENROLL)
        store.save_session(CHANNEL, sender, session)
        return
    session["uid"] = uid

    kind = msg.get("type")
    try:
        if kind == "text":
            _text(sender, uid, session, (msg.get("text") or {}).get("body") or "")
        elif kind in ("image", "document"):
            _media(sender, uid, session, msg.get(kind) or {})
        elif kind == "button":
            _text(sender, uid, session, (msg.get("button") or {}).get("text") or "")
        elif kind == "interactive":
            reply = msg.get("interactive") or {}
            picked = (reply.get("button_reply") or reply.get("list_reply") or {}).get("title") or ""
            _text(sender, uid, session, picked)
        else:
            _say(sender, copy.MEDIA_HELP)
    finally:
        store.save_session(CHANNEL, sender, session)


# ── What the patient said ─────────────────────────────────────────────────────────────


def _current_case(uid: str, session: dict) -> Case | None:
    """The case this conversation is about; newest first, remembering the choice."""
    case_id = session.get("case_id")
    if case_id:
        case = store.load_case(case_id)
        if case and case.owner == uid:
            return case
    cases = store.list_cases(uid)  # newest first
    case = cases[0] if cases else None
    if case:
        session["case_id"] = case.id
    return case


def _text(sender: str, uid: str, session: dict, body: str) -> None:
    word = copy.normalise(body)
    if not word:
        _say(sender, copy.HELP)
        return
    if session.get("muted") and word not in copy.AGENT_WORDS:
        return
    if word in copy.STOP_WORDS:
        session["muted"] = True
        _say(sender, copy.STOPPED)
        return
    if word in copy.AGENT_WORDS:
        session["muted"] = False
        _say(sender, copy.HELP)
        return

    case = _current_case(uid, session)

    if session.get("pending") == "delete":
        session["pending"] = None
        if word in copy.CONFIRM_WORDS and case:
            _erase(sender, case)
        else:
            _say(sender, "Nothing was deleted.")
        return

    if session.get("pending") == "choose":
        cases = store.list_cases(uid)
        index = copy.chosen_index(word, len(cases))
        if index is not None:
            session["pending"] = None
            session["case_id"] = cases[index].id
            _say(sender, "Switched.\n\n" + copy.status_text(cases[index]))
            return

    if word in copy.STATUS_WORDS:
        _say(sender, copy.status_text(case) if case else copy.NO_CASE)
    elif word in copy.CASES_WORDS:
        cases = store.list_cases(uid)
        if not cases:
            _say(sender, copy.NO_CASE)
        else:
            session["pending"] = "choose"
            _say(sender, copy.cases_text(cases, session.get("case_id")))
    elif word in copy.LETTER_WORDS:
        _letter(sender, case)
    elif word in copy.FORM_WORDS:
        _form(sender, case)
    elif word in copy.ANALYSE_WORDS:
        _analyse(sender, uid, case)
    elif word.startswith(("filed", "sent")):
        _filed(sender, case, body)
    elif word.startswith("reply"):
        _reply(sender, case, body)
    elif word in copy.PREDISCHARGE_WORDS:
        _predischarge(sender, uid, session)
        return
    elif word in copy.DELETE_WORDS:
        if not case:
            _say(sender, copy.NO_CASE)
        else:
            session["pending"] = "delete"
            _say(
                sender,
                "This erases the case and every document you sent, for good. "
                "Reply *DELETE YES* to confirm.",
            )
    elif not case:
        _say(sender, copy.NO_CASE)
    elif copy.needs_analysis(case):
        _say(sender, copy.NOT_READY)
    else:
        _answer(sender, uid, case, body)


def _answer(sender: str, uid: str, case: Case, question: str) -> None:
    """A free-text question, grounded in this case — the WhatsApp twin of POST /ask."""
    question = question.strip()[:1000]
    limit = get_settings().questions_per_day
    if not store.take_quota(f"ask-{uid}-{datetime.now(UTC):%Y%m%d}", limit):
        _say(sender, f"You can ask up to {limit} questions a day. Please try again tomorrow.")
        return
    answer = assistant.answer(case, question)
    now = datetime.now(UTC)
    case.events.append(CaseEvent(at=now, kind="message", text=question))
    case.events.append(CaseEvent(at=now, kind="ask", text=answer))
    store.save_case(case)
    _say(sender, answer)


def _analyse(sender: str, uid: str, case: Case | None) -> None:
    if not case:
        _say(sender, copy.NO_CASE)
        return
    if case.status == CaseStatus.ANALYSING:
        _say(sender, "I'm still reading this case — I'll message you the moment it's done.")
        return
    if case.documents_deleted_at:
        _say(
            sender,
            "This case's documents were deleted after it was resolved, so I can't reread it.",
        )
        return
    if not case.documents:
        _say(
            sender,
            "Send me the policy and the draft discharge summary first."
            if case.kind == CaseKind.PRE_DISCHARGE
            else "Send me the documents first — at least the rejection letter and the policy.",
        )
        return
    limit = get_settings().analyses_per_day
    if not store.take_quota(f"analyse-{uid}-{datetime.now(UTC):%Y%m%d}", limit):
        _say(sender, f"You can run up to {limit} analyses a day. Please try again tomorrow.")
        return
    case.status = CaseStatus.ANALYSING
    store.save_case(case)
    _say(
        sender,
        "Reading your documents now — decoding the rejection, finding the rules that apply and "
        "checking every source. This takes a minute or two.",
    )
    try:
        run_case(case.id)
    except Exception:
        log.exception("whatsapp: analysis failed for case %s", case.id)
    _say(sender, copy.result_text(store.load_case(case.id)))


# ── Documents ─────────────────────────────────────────────────────────────────────────


def _new_case(uid: str, phone: str, caption: str) -> Case:
    case = Case(
        id=uuid.uuid4().hex,
        owner=uid,
        created_at=datetime.now(UTC),
        country=copy.country_for_phone(phone),
        title=caption[:120] or None,
        title_auto=True,
    )
    store.save_case(case)
    return case


def _media(sender: str, uid: str, session: dict, media: dict) -> None:
    media_id = str(media.get("id") or "")
    if not media_id:
        _say(sender, copy.MEDIA_HELP)
        return

    case = _current_case(uid, session)
    if not case:
        case = _new_case(uid, accounts.to_e164(sender), (media.get("caption") or "").strip())
        session["case_id"] = case.id
    if len(case.documents) >= uploads.MAX_DOCUMENTS:
        _say(
            sender,
            f"A case can hold at most {uploads.MAX_DOCUMENTS} documents. "
            "Reply *DELETE* to start over.",
        )
        return

    try:
        data, mime, meta_name = wa.download_media(media_id)
    except wa.WhatsAppError as exc:
        log.warning("whatsapp: media %s for %s failed: %s", media_id, _mask(sender), exc)
        _say(sender, "I couldn't download that file. Please send it again.")
        return

    raw_name = media.get("filename") or meta_name or ""
    name = uploads.safe_name(raw_name) if raw_name else ""
    if Path(name).suffix.lower() not in uploads.ALLOWED:
        name = f"whatsapp{IMAGE_EXT.get(mime, '')}"
    if Path(name).suffix.lower() not in uploads.ALLOWED:
        _say(sender, "I can read PDFs and photos (JPG, PNG, WEBP). Please send it in one of those.")
        return
    if not data:
        _say(sender, "That file came through empty. Please send it again.")
        return

    doc_id = uuid.uuid4().hex
    uri = files.put(f"{case.id}/{doc_id}-{name}", data, mime)
    case.documents.append(
        Document(id=doc_id, filename=name, gcs_uri=uri, uploaded_at=datetime.now(UTC))
    )
    store.save_case(case)

    count = len(case.documents)
    reply = f"Got it — {name}. That's {count} document{'s' if count != 1 else ''} on this case."
    if case.status == CaseStatus.COLLECTING and not case.assessment:
        # Don't ask for the policy when the policy is what just arrived.
        reply += (
            "\n\nNow send the policy wording and the hospital papers."
            if count == 1
            else "\n\nSend anything else you have."
        )
        reply += " Reply *ANALYSE* when you've sent everything."
    _say(sender, reply)


def _locked(sender: str, case: Case) -> bool:
    """Payments are on and this case's appeal pack isn't unlocked: send them to the app.

    The app's own routes gate the PDFs on `payments.is_unlocked`, and the letter and form are
    built here rather than through those routes, so this channel has to apply the same gate —
    otherwise LETTER/FORM would hand the paid pack out for free.
    """
    if payments.is_unlocked(case):
        return False
    currency, amount = payments.price(case.country) or ("", 0)
    price = money(amount / 100, currency) if currency else "the appeal pack"
    link = f"{get_settings().app_url.rstrip('/')}/case/{case.id}"
    _say(
        sender,
        f"The appeal pack for this case isn't unlocked yet ({price}).\n\n"
        f"Unlock it in the Kavach app, then reply *LETTER* again:\n{link}",
    )
    return True


def _letter(sender: str, case: Case | None) -> None:
    if not case:
        _say(sender, copy.NO_CASE)
        return
    if not case.letter:
        _say(sender, "I haven't drafted the letter yet — reply *ANALYSE* first.")
        return
    if _locked(sender, case):
        return
    _document(
        sender,
        filing.render_letter_pdf(case.letter, local=case.language != "en"),
        "kavach-appeal-letter.pdf",
        "Your appeal letter. Check every detail before you sign or send it.",
    )


def _form(sender: str, case: Case | None) -> None:
    if not case or not case.assessment:
        _say(sender, "I need to read the case first — reply *ANALYSE*.")
        return
    if _locked(sender, case):
        return
    pack = filing.filing_pack(case)
    caption = f"{pack.form} for {pack.dispute_body}."
    if pack.missing:
        caption += " Still blank: " + ", ".join(pack.missing[:6]) + "."
    _document(sender, filing.render_pdf(pack, case), "kavach-filing.pdf", caption)


def _filed(sender: str, case: Case | None, body: str) -> None:
    """*FILED*: the patient sent the letter/form, so that step's countdown starts."""
    if not case:
        _say(sender, copy.NO_CASE)
        return
    if copy.needs_analysis(case):
        _say(sender, copy.NOT_READY)
        return
    now = datetime.now(UTC)
    when = copy.filed_date(body, now.date())
    if when is None:
        _say(sender, "I couldn't read that date. Reply *FILED* for today, or *FILED 2026-10-12*.")
        return
    if when > now.date():
        _say(sender, "That date is in the future — reply *FILED* for today.")
        return
    case = escalation.mark_filed(case, FiledRequest(filed_on=when), now)
    store.save_case(case)
    _say(sender, copy.filed_text(case, when))


def _reply(sender: str, case: Case | None, body: str) -> None:
    """*REPLY PAID 112000*: the insurer answered; resolve the case or escalate a step."""
    if not case:
        _say(sender, copy.NO_CASE)
        return
    if case.status not in (CaseStatus.FILED, CaseStatus.ESCALATED):
        _say(
            sender,
            "I don't have this case as filed yet. Reply *FILED* once you've sent the form, "
            "then tell me their reply.",
        )
        return
    parsed = copy.reply_request(body, datetime.now(UTC).date())
    if parsed is None:
        _say(
            sender,
            "Tell me what they said, like:\n"
            "• *REPLY PAID 112000*\n• *REPLY PARTLY 20000*\n• *REPLY REJECTED*",
        )
        return
    outcome, amount = parsed
    replied_with = copy.step_name(case)  # capture before record_reply moves the ladder
    case = escalation.record_reply(
        case,
        ReplyRequest(outcome=outcome, replied_on=datetime.now(UTC).date(), amount_paid=amount),
        datetime.now(UTC),
    )
    store.save_case(case)
    _say(sender, copy.reply_text(case, outcome, amount, replied_with))


def _predischarge(sender: str, uid: str, session: dict) -> None:
    """Start a pre-discharge check: the claim has not been filed yet, so nothing is rejected."""
    case = Case(
        id=uuid.uuid4().hex,
        owner=uid,
        created_at=datetime.now(UTC),
        kind=CaseKind.PRE_DISCHARGE,
        country=copy.country_for_phone(accounts.to_e164(sender)),
    )
    store.save_case(case)
    # Mutate the session `_message` owns: it persists it in its own `finally`, and a second
    # load/save here would be overwritten by that stale copy.
    session["case_id"] = case.id
    _say(
        sender,
        "Started a *pre-discharge check*. Send me the policy, the policy schedule, the draft "
        "discharge summary and the interim bill — I'll tell you what the insurer may cut before "
        "you leave hospital. Then reply *ANALYSE*.",
    )


def _erase(sender: str, case: Case) -> None:
    """The same promise the app makes: DELETE /cases/{id} removes files and the case."""
    files.delete_case_files(case.id)
    store.delete_case(case.id)
    _say(sender, "Deleted. The case and every document you sent are gone.")


# ── Outbound wrappers ─────────────────────────────────────────────────────────────────


def _read(message_id: str) -> None:
    """Blue ticks. Never fatal: an unread receipt must not cost the patient their answer."""
    try:
        wa.mark_read(message_id)
    except wa.WhatsAppError as exc:
        log.debug("whatsapp: could not mark %s read: %s", message_id, exc)


def _say(to: str, body: str) -> None:
    try:
        wa.send_text(to, body)
    except wa.WhatsAppError as exc:
        log.error("whatsapp: reply to %s failed: %s", _mask(to), exc)


def _document(to: str, data: bytes, filename: str, caption: str) -> None:
    try:
        wa.send_media(to, data, filename, "application/pdf", caption=caption)
    except wa.WhatsAppError as exc:
        log.error("whatsapp: %s to %s failed: %s", filename, _mask(to), exc)


def notify_case(case: Case, text: str) -> int:
    """Push a proactive update to the owner's WhatsApp, if they use the channel.

    Returns how many messages actually went out. Reminders are best-effort by design: the daily
    tracker must not fail because Meta is having a bad day.
    """
    sent = 0
    for phone, session in store.sessions_for(case.owner):
        if session.get("muted"):
            continue
        try:
            outcome = wa.send_notice(phone, text, session.get("last_in_at"))
        except wa.WhatsAppError as exc:
            log.warning("whatsapp: notice to %s failed: %s", _mask(phone), exc)
            continue
        if outcome != "skipped":
            sent += 1
    return sent
