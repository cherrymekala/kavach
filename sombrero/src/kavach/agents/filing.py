"""Filing agent: draft the appeal letter and fill the dispute-body form."""
from ..models import Case
from ..tools import packs
from . import llm, prompts


def draft_letter(case: Case) -> str:
    return llm.text(prompts.LETTER, context={
        "language": case.language,
        "facts": case.facts.model_dump(mode="json") if case.facts else {},
        "arguments": [a.model_dump() for a in (case.assessment.arguments if case.assessment else [])],
    })


def form_fields(case: Case) -> dict:
    template = packs.load(case.country)["dispute_process"][case.escalation_step]
    # TODO(week 2): map case facts onto template["form_fields"] and render a PDF.
    return {"form": template.get("form"), "fields": template.get("form_fields", [])}
