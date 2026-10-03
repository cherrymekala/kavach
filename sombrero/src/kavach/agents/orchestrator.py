"""Runs the pipeline for one case and writes progress to Firestore as it goes.

Plain Python so each step is easy to debug; `analyse` has no storage dependency so the
whirlpool evals run exactly the same steps as the API.
"""

from collections.abc import Callable
from dataclasses import dataclass

from ..models import Assessment, CaseFacts, CaseStatus, Document
from ..tools import rulings, store
from . import checker, code_decoder, filing, intake, policy_rules, strategist


@dataclass
class Analysis:
    facts: CaseFacts
    sections: list[dict]
    similar: list[dict]
    draft: Assessment  # before the checker
    assessment: Assessment  # after the checker


def analyse(
    documents: list[Document], country: str, progress: Callable[[str], None] = lambda _: None
) -> Analysis:
    progress("Reading your documents")
    result = intake.run([d.gcs_uri for d in documents])
    for label in result.documents:
        if 0 <= label.index < len(documents):
            documents[label.index].doc_type = label.doc_type
            documents[label.index].warning = label.warning
    facts = result.facts

    progress("Decoding the rejection")
    decoded = code_decoder.decode(country, facts.tpa, facts.rejection_code)
    if decoded:
        # An exact code match beats the model's reading of the letter.
        facts.rejection_category = decoded["category"]
        if not facts.rejection_reason:
            facts.rejection_reason = decoded.get("meaning")

    progress("Finding the rules that apply")
    sections = policy_rules.find_sections(country, policy_rules.describe(facts))

    progress("Looking up similar past cases")
    similar = rulings.search_similar(facts, country)

    progress("Building your case")
    draft = strategist.assess(facts, documents, sections, similar)

    progress("Checking every source")
    assessment = checker.verify(draft, documents, sections, similar)
    return Analysis(facts, sections, similar, draft, assessment)


def run_case(case_id: str) -> None:
    case = store.load_case(case_id)

    def progress(text: str | None) -> None:
        case.progress = text
        store.save_case(case)

    try:
        result = analyse(case.documents, case.country, progress)
        case.facts, case.assessment = result.facts, result.assessment

        progress("Writing your appeal")
        case.letter = filing.draft_letter(case)

        case.status = CaseStatus.READY
        progress(None)
    except Exception:
        case.status = CaseStatus.COLLECTING
        progress("We couldn't finish the analysis. Please try again.")
        raise
