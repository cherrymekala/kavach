"""WhatsApp copy and intent rules.

Kept away from the webhook router so the wording, the commands and the intent matching can be
read and unit-tested without Meta's payload shape around them. The router owns all I/O.

WhatsApp formatting is limited to *bold*, _italic_ and ```monospace``` — no Markdown headings or
links-as-text — so the replies here stay plain and short enough for a phone screen.
"""

from datetime import UTC, date, datetime, timedelta

from ..models import Case, CaseStatus
from ..tools.money import money

AGENT_WORDS = {"hi", "hello", "hey", "menu", "help", "kavach", "start", "resume", "unstop"}
STATUS_WORDS = {"status", "where", "update", "progress", "deadline"}
CASES_WORDS = {"cases", "case", "switch"}
LETTER_WORDS = {"letter", "appeal", "draft"}
FORM_WORDS = {"form", "filing", "file"}
ANALYSE_WORDS = {"analyse", "analyze", "run", "go", "read"}
DELETE_WORDS = {"delete", "erase", "remove my data", "forget"}
PREDISCHARGE_WORDS = {
    "predischarge",
    "pre-discharge",
    "before discharge",
    "in hospital",
    "admitted",
}
CONFIRM_WORDS = {"yes", "y", "yes delete", "delete yes", "confirm", "ok", "okay"}
STOP_WORDS = {"stop", "unsubscribe", "mute", "pause"}

HELP = (
    "*Kavach* — I help you fight a health-insurance claim rejection.\n\n"
    "Send me the documents, as photos or PDFs:\n"
    "1. the letter or email that rejected or cut your claim\n"
    "2. your policy wording or schedule\n"
    "3. the hospital discharge summary and bill\n\n"
    "Then reply *ANALYSE*. I'll read them, decode the rejection, find the rules that apply and "
    "write your appeal letter.\n\n"
    "Any time:\n"
    "• *STATUS* — where the case stands and the next deadline\n"
    "• *LETTER* — your appeal letter as a PDF\n"
    "• *FORM* — the official form for your next dispute step\n"
    "• *FILED* — you sent it; start that step's countdown\n"
    "• *REPLY* — they answered (e.g. _REPLY PAID 112000_)\n"
    "• *CASES* — switch between your cases\n"
    "• *PREDISCHARGE* — check a claim before you are discharged\n"
    "• *DELETE* — erase this case and its documents\n"
    "• *STOP* — stop the reminders I send you\n\n"
    "Or just ask me a question about the case."
)

ENROLL = (
    "Welcome to Kavach. I can't find a case for this number yet.\n\n"
    "Sign in to Kavach with this same phone number and your cases will appear here — WhatsApp "
    "and the app share one account, so there is nothing to link."
)

MEDIA_HELP = (
    "I can read photos and PDFs (up to 20 MB each), but not voice notes or videos yet. "
    "Please send the document as a photo or a PDF."
)

NO_CASE = (
    "You don't have a case yet. Send me a photo or PDF of the letter that rejected your claim "
    "and I'll start one."
)

NOT_READY = "I haven't read this case yet. Send the documents you have, then reply *ANALYSE*."

STOPPED = (
    "Done — I won't message you unless you ask. Reply *START* when you want the reminders back."
)

DISCLAIMER = (
    "Kavach prepares documents from your files and public rules to help you raise a dispute. "
    "It is not legal advice. Check every detail before you sign or send anything."
)


def normalise(text: str) -> str:
    """Lower-case, collapse whitespace, drop trailing punctuation: "Status!" -> "status"."""
    return " ".join((text or "").strip().lower().split()).strip(".!?।,")


def country_for_phone(phone: str) -> str:
    """Same guess as the web app's `countryFromPhone`, so a case starts in the right country."""
    if phone.startswith("+65"):
        return "SG"
    if phone.startswith("+60"):
        return "MY"
    return "IN"


def _ladder_step(case: Case, index: int) -> dict:
    from ..tools import packs

    steps = packs.load(case.country)["dispute_process"]
    return steps[min(index, len(steps) - 1)]


def status_text(case: Case, now: datetime | None = None) -> str:
    """Where the case stands: what it is, how strong, and what is due next."""
    now = now or datetime.now(UTC)
    lines = [f"*{case.title or 'Your claim'}*"]

    if case.facts:
        bits = [b for b in (case.facts.insurer, case.facts.diagnosis) if b]
        if bits:
            lines.append(" · ".join(bits))
        if case.facts.claim_amount:
            lines.append(f"Claim: {money(case.facts.claim_amount, case.facts.currency)}")

    labels = {
        CaseStatus.COLLECTING: "waiting for your documents",
        CaseStatus.ANALYSING: "reading your documents",
        CaseStatus.READY: "analysis ready",
        CaseStatus.FILED: f"filed with {_ladder_step(case, case.escalation_step)['step']}",
        CaseStatus.ESCALATED: f"escalated to {_ladder_step(case, case.escalation_step)['step']}",
        CaseStatus.RESOLVED: "resolved",
    }
    lines.append(f"Status: {labels.get(case.status, case.status.value)}")

    if case.assessment:
        lines.append(f"Strength: {case.assessment.strength}")
    if case.discharge_check:
        lines.append(f"Verdict: {case.discharge_check.verdict.replace('_', ' ')}")
    if case.amount_recovered:
        currency = case.facts.currency if case.facts else None
        lines.append(f"Recovered: {money(case.amount_recovered, currency)}")

    if case.next_deadline:
        days = (case.next_deadline.date() - now.date()).days
        when = case.next_deadline.strftime("%d %b %Y")
        left = f"{days} day{'s' if days != 1 else ''} left" if days >= 0 else "overdue"
        lines.append(f"Next deadline: {when} ({left})")
    elif case.status in (CaseStatus.READY, CaseStatus.ESCALATED):
        nxt = _ladder_step(case, case.escalation_step)
        lines.append(f"Next step: {nxt['form']} for {nxt['step']}")

    if case.events:
        lines.append(f"\nLatest: {case.events[-1].text}")
    # Wherever the assessment or the pre-discharge verdict appears, the disclaimer goes with it.
    if case.assessment or case.discharge_check:
        lines.append(f"\n_{DISCLAIMER}_")
    return "\n".join(lines)


def result_text(case: Case) -> str:
    """The message sent when an analysis finishes (or fails)."""
    if case.status != CaseStatus.READY:
        return (
            f"I couldn't finish reading this case.\n\n{case.progress or 'Please try again.'}"
            "\n\nSend anything that's missing and reply *ANALYSE* again."
        )
    if case.discharge_check:
        check = case.discharge_check
        lines = [f"*Pre-discharge check: {check.verdict.replace('_', ' ')}*", check.summary]
        for risk in check.risks[:3]:
            lines.append(f"\n*{risk.title}*\n{risk.fix}")
        lines.append(f"\n_{DISCLAIMER}_")
        return "\n".join(lines)

    lines = []
    if case.assessment:
        lines.append(f"*Done — your case looks {case.assessment.strength}.*")
        if case.assessment.arguments:
            lines.append(f"{len(case.assessment.arguments)} sourced arguments.")
        if case.assessment.similar_cases_total:
            lines.append(
                f"Similar past cases: won {case.assessment.similar_cases_won} "
                f"of {case.assessment.similar_cases_total}."
            )
        if case.assessment.missing_documents:
            lines.append("\nStill needed:")
            lines += [f"• {d}" for d in case.assessment.missing_documents]
    step = _ladder_step(case, case.escalation_step)
    if case.letter:
        lines.append("\nI've drafted your appeal letter — reply *LETTER* for the PDF.")
    lines.append(f"First step: {step['form']} for {step['step']} — reply *FORM* to get it.")
    lines.append(f"\n_{DISCLAIMER}_")
    return "\n".join(lines)


def cases_text(cases: list[Case], current_id: str | None) -> str:
    """A numbered list, so the next message can be a bare digit."""
    lines = ["*Your cases*"]
    for i, case in enumerate(cases[:5], start=1):
        mark = "•" if case.id == current_id else " "
        title = case.title or "Claim"
        lines.append(f"{mark} {i}. {title} — {case.status.value}")
    lines.append("\nReply with a number to switch to that case.")
    return "\n".join(lines)


def chosen_index(text: str, count: int) -> int | None:
    """A bare digit 1..count (the reply to `cases_text`), else None."""
    word = normalise(text)
    if word.isdigit() and 1 <= int(word) <= min(count, 5):
        return int(word) - 1
    return None


# ── The tracker, driven from a chat ───────────────────────────────────────────────────


def filed_date(text: str, today: date) -> date | None:
    """The date the patient says they filed: *FILED*, *FILED 2026-10-12* or *FILED 12/10/2026*.

    None means "we could not read that", which the router reports back rather than silently
    guessing — a wrong filing date starts the wrong countdown.
    """
    words = normalise(text).replace("filed", " ", 1).replace("sent", " ", 1).split()
    if not words:
        return today
    for word in words:
        if word in ("today", "now", "just"):
            return today
        if word == "yesterday":
            return today - timedelta(days=1)
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
            try:
                # Only the calendar date is used, so the naive parse is what we want here.
                return datetime.strptime(word, fmt).date()  # noqa: DTZ007
            except ValueError:
                continue
    return None


def reply_request(text: str, today: date) -> tuple[str, float | None] | None:
    """Parse *REPLY PAID 112000* / *REPLY PARTLY 20000* / *REPLY REJECTED*.

    Returns (outcome, amount) or None when the outcome is not one we can act on.
    """
    words = normalise(text).replace("reply", " ", 1).split()
    if not words:
        return None
    head, rest = words[0], words[1:]
    outcome = {
        "paid": "paid",
        "received": "paid",
        "partly": "partly_paid",
        "partial": "partly_paid",
        "partly_paid": "partly_paid",
        "rejected": "rejected",
        "refused": "rejected",
        "no": "rejected",
    }.get(head)
    if outcome is None:
        return None
    digits = "".join(ch for ch in " ".join(rest) if ch.isdigit())
    return outcome, (float(digits) if digits else None)


def filed_text(case: Case, when: date) -> str:
    deadline = f"{case.next_deadline:%d %b %Y}" if case.next_deadline else "not set"
    step = _ladder_step(case, case.escalation_step)
    return (
        f"Noted — filed with *{step['step']}* on {when:%d %b %Y}.\n\n"
        f"I'll remind you by *{deadline}*. If they haven't replied by then, reply *STATUS* and "
        "I'll move you to the next step."
    )


def step_name(case: Case) -> dict:
    """The rung of the ladder the case is on *now*.

    Called before something moves it: a rejection escalates the case, so reading the step
    afterwards would name the next dispute body as the one that refused.
    """
    return _ladder_step(case, case.escalation_step)


def reply_text(case: Case, outcome: str, amount: float | None, replied: dict) -> str:
    currency = case.facts.currency if case.facts else None
    if case.status == CaseStatus.RESOLVED:
        recovered = money(amount, currency) if amount else ""
        head = f"*Resolved.* {recovered} recovered." if recovered else "*Resolved.*"
        return f"{head}\n\nGlad it worked. Keep the settlement letter somewhere safe."
    step = step_name(case)
    what = {"paid": "paid", "partly_paid": "paid in part", "rejected": "refused"}[outcome]
    return (
        f"Noted — {replied['step']} {what}"
        + (f" ({money(amount, currency)})" if amount else "")
        + f".\n\nNext: *{step['form']}* for *{step['step']}*. Reply *FORM* and I'll send it."
    )


def needs_analysis(case: Case) -> bool:
    return not case.assessment and not case.discharge_check
