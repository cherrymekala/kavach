"""Pre-discharge check: what is likely to get a claim rejected or cut, while the patient is still
in hospital and it can be fixed.

Reuses the dispute pipeline's intake, regulation tree search and checker; only the reasoning step
differs. Every risk must quote the policy, a regulation or the patient's own papers, and risks
whose quotes the checker cannot find are dropped.
"""

from collections.abc import Callable

from pydantic import BaseModel

from ..models import Argument, Assessment, CaseFacts, DischargeCheck, DocType, Document, Risk
from . import checker, intake, llm, policy_rules, prompts

NEEDS = (
    "Please upload your policy and the hospital's discharge summary or bill, "
    "so we can check them against each other."
)
ORDER = {"high": 0, "medium": 1, "low": 2}


class NotEnoughDocuments(Exception):
    """A policy plus a discharge summary or bill is the minimum for a useful check."""


class _Draft(BaseModel):
    verdict: str
    summary: str
    risks: list[Risk]


def describe(facts: CaseFacts) -> str:
    """Question for the regulation tree search: the admission, not a rejection."""
    known = {
        "diagnosis": facts.diagnosis,
        "admission_date": facts.admission_date,
        "policy_start": facts.policy_start,
        "months_of_continuous_cover": policy_rules.months_of_cover(facts),
    }
    details = "; ".join(f"{k}: {v}" for k, v in known.items() if v is not None)
    return (
        "Pre-discharge check of a hospital claim before it is filed. Likely issues: room rent "
        "limits and proportionate deduction, non-payable items, waiting periods and "
        f"pre-existing diseases, the definition of hospitalization. {details}"
    )


def _verify(risks: list[Risk], documents: list[Document], sections: list[dict]) -> list[Risk]:
    # The checker works on arguments; use the index as the claim so risks can be matched back.
    as_args = [
        Argument(claim=str(i), explanation="", sources=r.sources) for i, r in enumerate(risks)
    ]
    checked = checker.verify(
        Assessment(strength="medium", score=0.5, arguments=as_args), documents, sections, []
    )
    kept = [
        risks[int(a.claim)].model_copy(update={"sources": a.sources}) for a in checked.arguments
    ]
    return sorted(kept, key=lambda r: ORDER.get(r.severity, 1))


def check(
    documents: list[Document], country: str, progress: Callable[[str], None] = lambda _: None
) -> tuple[CaseFacts, DischargeCheck]:
    progress("Reading your documents")
    result = intake.run([d.gcs_uri for d in documents])
    for label in result.documents:
        if 0 <= label.index < len(documents):
            documents[label.index].doc_type = label.doc_type
            documents[label.index].warning = label.warning
    kinds = {d.doc_type for d in documents}
    if DocType.POLICY not in kinds or not kinds & {DocType.DISCHARGE_SUMMARY, DocType.BILL}:
        raise NotEnoughDocuments(NEEDS)
    facts = result.facts

    progress("Finding the rules that apply")
    sections = policy_rules.find_sections(country, describe(facts))

    progress("Checking your bill against the policy")
    context = {
        "facts": facts.model_dump(mode="json"),
        "months_of_continuous_cover": policy_rules.months_of_cover(facts),
        "documents": [
            {"file_index": i, "type": d.doc_type, "name": d.filename}
            for i, d in enumerate(documents)
        ],
        "regulations": sections,
    }
    draft = llm.structured(
        prompts.DISCHARGE, [d.gcs_uri for d in documents], _Draft, context=context
    )

    progress("Checking every source")
    risks = _verify(draft.risks, documents, sections)
    if not risks:
        verdict = "clear"
    elif any(r.severity == "high" for r in risks):
        verdict = "high_risk"
    else:
        verdict = "some_risks"
    # The verdict follows the verified risks, not the draft: dropped risks can't raise it.
    return facts, DischargeCheck(verdict=verdict, summary=draft.summary, risks=risks)
