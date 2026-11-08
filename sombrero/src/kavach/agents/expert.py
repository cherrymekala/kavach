"""Handoff to a human advocate: when to offer it, and what the triage team sees.

The team gets a summary only (never the documents), and only after the patient consents on
a screen that lists exactly these fields.
"""

from ..models import Case
from ..tools import packs

SHARED = [
    "country",
    "insurer",
    "rejection reason and category",
    "claim amount and amount paid",
    "Kavach's assessment (strength, number of arguments)",
    "next deadline and current step",
    "your name, phone and email as you give them",
    "your note",
]


def offer_reason(case: Case) -> str | None:
    """Why to suggest a human now: a weak case, or a lot of money. None = available, not pushed."""
    if case.assessment and case.assessment.strength == "weak":
        return "weak"
    threshold = packs.load(case.country).get("expert_threshold")
    amount = case.facts.claim_amount if case.facts else None
    if threshold and amount and amount >= threshold:
        return "high_value"
    return None


def summary(case: Case) -> dict:
    facts, assessment = case.facts, case.assessment
    return {
        "title": case.title,
        "kind": str(case.kind),
        "country": case.country,
        "language": case.language,
        "insurer": facts.insurer if facts else None,
        "rejection_reason": facts.rejection_reason if facts else None,
        "rejection_category": facts.rejection_category if facts else None,
        "claim_amount": facts.claim_amount if facts else None,
        "amount_approved": facts.amount_approved if facts else None,
        "currency": facts.currency if facts else None,
        "strength": assessment.strength if assessment else None,
        "arguments": len(assessment.arguments) if assessment else 0,
        "status": str(case.status),
        "escalation_step": case.escalation_step,
        "next_deadline": case.next_deadline.isoformat() if case.next_deadline else None,
        "patient_name": case.complainant.name if case.complainant else None,
    }


def email_text(
    summary: dict, phone: str | None, email: str | None, note: str, reason: str | None
) -> str:
    lines = [f"New expert request ({reason or 'patient asked'})", ""]
    lines += [f"{k}: {v}" for k, v in summary.items() if v not in (None, "")]
    lines += [
        "",
        f"phone: {phone or '-'}",
        f"email: {email or '-'}",
        "",
        "Patient's note:",
        note or "-",
    ]
    lines += ["", "The patient consented to share this summary. Their documents stay in Kavach."]
    return "\n".join(lines)
