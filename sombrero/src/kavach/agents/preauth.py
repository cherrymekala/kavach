"""Cashless refused in hospital: what to do in the next few hours.

Fast on purpose: intake, the refusal code, the country's cashless rules (pack
`cashless_rules`) plus a regulation tree search, one reasoning step, then the checker. No
precedent search: the patient needs an answer while the hospital desk is still waiting. Quotes
the checker cannot find are dropped; practical steps without a source stay.
"""

from collections.abc import Callable

from pydantic import BaseModel

from ..models import (
    Argument,
    Assessment,
    CaseFacts,
    DocType,
    Document,
    PreauthAction,
    PreauthCheck,
    Source,
)
from ..tools import packs
from . import checker, code_decoder, intake, llm, policy_rules, prompts

NEEDS = (
    "Please upload the message refusing or querying the cashless request "
    "(a photo of the letter, email or SMS is fine)."
)


class NotEnoughDocuments(Exception):
    """Nothing in the uploads shows a cashless refusal or query."""


class _Draft(BaseModel):
    status: str
    summary: str
    actions: list[PreauthAction]
    doctor_note: str
    request: str
    fallback: str
    rules: list[Source]


def describe(facts: CaseFacts) -> str:
    """Question for the regulation tree search: a cashless refusal during admission."""
    known = {
        "diagnosis": facts.diagnosis,
        "reason given": facts.rejection_reason,
        "admission_date": facts.admission_date,
        "months_of_continuous_cover": policy_rules.months_of_cover(facts),
    }
    details = "; ".join(f"{k}: {v}" for k, v in known.items() if v is not None)
    return (
        "Cashless pre-authorisation refused or queried while the patient is in hospital. "
        f"Time limits for cashless decisions and discharge, and the reason given. {details}"
    )


def _sections(country: str, facts: CaseFacts) -> list[dict]:
    fixed = policy_rules.sections_by_ref(country, packs.load(country).get("cashless_rules", []))
    found = policy_rules.find_sections(country, describe(facts))
    seen = {s["ref"] for s in fixed}
    return fixed + [s for s in found if s["ref"] not in seen]


def _verify(draft: _Draft, documents: list[Document], sections: list[dict]) -> _Draft:
    # The checker works on arguments: one per action, plus one for the rules, matched by index.
    groups = [a.sources for a in draft.actions] + [draft.rules]
    as_args = [Argument(claim=str(i), explanation="", sources=s) for i, s in enumerate(groups) if s]
    checked = checker.verify(
        Assessment(strength="medium", score=0.5, arguments=as_args), documents, sections, []
    )
    verified = {int(a.claim): a.sources for a in checked.arguments}
    actions = [
        a.model_copy(update={"sources": verified.get(i, [])}) for i, a in enumerate(draft.actions)
    ]
    rules = list({r.ref: r for r in verified.get(len(draft.actions), [])}.values())
    return draft.model_copy(update={"actions": actions, "rules": rules})


def check(
    documents: list[Document], country: str, progress: Callable[[str], None] = lambda _: None
) -> tuple[CaseFacts, PreauthCheck]:
    progress("Reading your documents")
    result = intake.run([d.gcs_uri for d in documents])
    for label in result.documents:
        if 0 <= label.index < len(documents):
            documents[label.index].doc_type = label.doc_type
            documents[label.index].warning = label.warning
    facts = result.facts
    has_letter = any(d.doc_type == DocType.REJECTION_LETTER for d in documents)
    if not has_letter and not facts.rejection_reason:
        raise NotEnoughDocuments(NEEDS)
    decoded = code_decoder.decode(country, facts.tpa, facts.rejection_code)
    if decoded:
        facts.rejection_category = decoded["category"]
        if not facts.rejection_reason:
            facts.rejection_reason = decoded.get("meaning")

    progress("Finding the rules that apply")
    sections = _sections(country, facts)

    progress("Planning your next steps")
    context = {
        "facts": facts.model_dump(mode="json"),
        "decoded_code": decoded,
        "months_of_continuous_cover": policy_rules.months_of_cover(facts),
        "documents": [
            {"file_index": i, "type": d.doc_type, "name": d.filename}
            for i, d in enumerate(documents)
        ],
        "regulations": sections,
        # The only contact the plan may name: the official grievance address from the pack.
        "insurer_contact": packs.insurer_contact(country, facts.insurer),
    }
    draft = llm.structured(prompts.PREAUTH, [d.gcs_uri for d in documents], _Draft, context=context)

    progress("Checking every source")
    draft = _verify(draft, documents, sections)
    return facts, PreauthCheck(**draft.model_dump())
