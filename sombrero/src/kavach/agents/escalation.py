"""Escalation tracker: the dispute ladder from the country pack, driven by dates.

Pure state changes on a Case (no I/O) so they are unit-testable; the router and the daily
Cloud Scheduler tick do the loading and saving. Steps come from `dispute_process` in the pack.
"""

from datetime import UTC, date, datetime, time, timedelta

from ..models import Case, CaseEvent, CaseStatus, FiledRequest, ReplyRequest
from ..tools import packs

LIMITATION_WARN_DAYS = 60


def _steps(case: Case) -> list[dict]:
    return packs.load(case.country)["dispute_process"]


def _end_of_day(d: date) -> datetime:
    return datetime.combine(d, time(23, 59), tzinfo=UTC)


def _log(case: Case, now: datetime, kind: str, text: str) -> None:
    case.events.append(CaseEvent(at=now, kind=kind, text=text, step=case.escalation_step))


def mark_filed(case: Case, req: FiledRequest, now: datetime) -> Case:
    steps = _steps(case)
    case.escalation_step = min(
        req.step if req.step is not None else case.escalation_step, len(steps) - 1
    )
    step = steps[case.escalation_step]
    case.status = CaseStatus.FILED
    case.next_deadline = _end_of_day(req.filed_on + timedelta(days=step["deadline_days"]))
    _log(
        case,
        now,
        "filed",
        f"Filed with {step['step']} on {req.filed_on:%d %b %Y}. Reply due by {case.next_deadline:%d %b %Y}.",
    )
    return case


def _escalate(case: Case, now: datetime, why: str) -> None:
    steps = _steps(case)
    if case.escalation_step + 1 >= len(steps):
        case.status = CaseStatus.ESCALATED
        case.next_deadline = None
        _log(
            case,
            now,
            "reminder",
            f"{why} This was the last step: follow up with {steps[-1]['step']} directly.",
        )
        return
    case.escalation_step += 1
    case.status = CaseStatus.ESCALATED
    case.next_deadline = None
    _log(
        case,
        now,
        "escalated",
        f"{why} Your {steps[case.escalation_step]['form']} for {steps[case.escalation_step]['step']} is ready to review and file.",
    )


def record_reply(case: Case, req: ReplyRequest, now: datetime) -> Case:
    step = _steps(case)[case.escalation_step]["step"]
    if req.outcome == "paid":
        case.status = CaseStatus.RESOLVED
        case.next_deadline = None
        case.amount_recovered = req.amount_paid or (case.facts.claim_amount if case.facts else None)
        _log(case, now, "resolved", f"{step} agreed to pay on {req.replied_on:%d %b %Y}.")
        return case
    paid = f" and paid {req.amount_paid:,.0f}" if req.amount_paid else ""
    if req.amount_paid:
        case.amount_recovered = (case.amount_recovered or 0) + req.amount_paid
    _log(
        case,
        now,
        "reply",
        f"{step} replied on {req.replied_on:%d %b %Y}: {req.outcome.replace('_', ' ')}{paid}.",
    )
    _escalate(case, now, "The reply did not resolve the claim.")
    return case


def tick(case: Case, now: datetime) -> bool:
    """Daily check for one case. Returns True if the case changed."""
    changed = False
    if case.status == CaseStatus.FILED and case.next_deadline and case.next_deadline <= now:
        step = _steps(case)[case.escalation_step]
        _escalate(case, now, f"No reply from {step['step']} within {step['deadline_days']} days.")
        changed = True
    limit = packs.load(case.country).get("limitation")
    rejected = case.facts.rejection_date if case.facts else None
    if limit and rejected and case.status != CaseStatus.RESOLVED:
        days_left = (rejected + timedelta(days=limit["days"]) - now.date()).days
        already = any(e.kind == "warning" for e in case.events)
        if 0 <= days_left <= LIMITATION_WARN_DAYS and not already:
            _log(
                case,
                now,
                "warning",
                f"Only {days_left} days left to approach the {limit['body']} "
                f"(time limit counted from {limit['from']}).",
            )
            changed = True
    return changed
