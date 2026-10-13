"""Free-text questions about a case, grounded in its facts and assessment."""

from ..models import Case
from . import llm

SYSTEM = (
    "You are Kavach, an assistant that helps a patient fight a health-insurance claim rejection. "
    "Answer the question using only the case facts and assessment you are given. "
    "When a source is cited, keep the reference. If the answer is not in the case, say so plainly "
    "and suggest what the patient could check. Be clear, calm and concise. Do not invent facts."
)


def answer(case: Case, question: str) -> str:
    context = {
        "question": question,
        "facts": case.facts.model_dump(mode="json") if case.facts else None,
        "assessment": case.assessment.model_dump(mode="json") if case.assessment else None,
    }
    return llm.text(SYSTEM, context)