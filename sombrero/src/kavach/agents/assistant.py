"""Free-text questions about a case, grounded in its facts and assessment."""

from ..models import Case
from . import llm

SYSTEM = (
    "You are Kavach, an assistant that helps a patient with a health-insurance claim: fighting a "
    "rejection, or checking a claim before discharge from hospital. "
    "Answer the question using only the case facts, assessment and discharge check you are given. "
    "When a source is cited, keep the reference. If the answer is not in the case, say so plainly "
    "and suggest what the patient could check. Be clear, calm and concise. Do not invent facts."
)

# Before any analysis there is nothing case-specific to ground on, but the patient still
# deserves an answer (greetings, "what is this?", "what should I upload?", general claim questions).
BEFORE_ANALYSIS = (
    "You are Kavach, an assistant that helps patients with health-insurance claims: fighting a "
    "rejected claim, a refused cashless approval in hospital, or checking a bill before discharge. "
    "The patient has not uploaded documents or run an analysis yet. Reply helpfully and briefly "
    "(2-5 short sentences) to whatever they say, including greetings and general questions about "
    "health insurance claims. Do not judge their chances or quote specific rules, clauses or past "
    "cases: that needs their documents. When it fits, tell them the next step: attach the "
    "rejection letter, the policy document and hospital bills or discharge summary with the "
    "paperclip, or tap the mic to tell the story by voice, then run the analysis. If they ask for "
    "something unrelated to insurance or health claims, say kindly that you can only help with "
    "their claim. Reply in the language they wrote in (the case language code is given). "
    "Never ask for policy, claim or ID numbers."
)

HISTORY = 10  # recent chat turns sent along, so follow-ups make sense


def _history(case: Case) -> list[dict]:
    turns = [e for e in case.events if e.kind in ("message", "ask")][-HISTORY:]
    return [{"who": "patient" if e.kind == "message" else "kavach", "text": e.text} for e in turns]


def answer(case: Case, question: str) -> str:
    if not (case.assessment or case.discharge_check or case.preauth_check):
        return llm.text(
            BEFORE_ANALYSIS,
            {
                "question": question,
                "case_language": case.language,
                "case_kind": case.kind,
                "documents_uploaded": len(case.documents),
                "earlier_messages": _history(case),
            },
        )
    context = {
        "question": question,
        "earlier_messages": _history(case),
        "facts": case.facts.model_dump(mode="json") if case.facts else None,
        "assessment": case.assessment.model_dump(mode="json") if case.assessment else None,
        "discharge_check": (
            case.discharge_check.model_dump(mode="json") if case.discharge_check else None
        ),
        "preauth_check": case.preauth_check.model_dump(mode="json") if case.preauth_check else None,
    }
    return llm.text(SYSTEM, context)
