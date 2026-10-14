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


def answer(case: Case, question: str) -> str:
    context = {
        "question": question,
        "facts": case.facts.model_dump(mode="json") if case.facts else None,
        "assessment": case.assessment.model_dump(mode="json") if case.assessment else None,
        "discharge_check": (
            case.discharge_check.model_dump(mode="json") if case.discharge_check else None
        ),
    }
    return llm.text(SYSTEM, context)