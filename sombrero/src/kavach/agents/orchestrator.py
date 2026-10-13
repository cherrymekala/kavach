"""Runs the pipeline for one case and writes progress to Firestore as it goes.

Plain Python so each step is easy to debug; `analyse` has no storage dependency so the
whirlpool evals run exactly the same steps as the API.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from ..config import get_settings
from ..models import Assessment, CaseEvent, CaseFacts, CaseStatus, DocType, Document
from ..tools import rulings, store
from . import checker, code_decoder, filing, intake, policy_rules, strategist

log = logging.getLogger("kavach.orchestrator")

NO_REJECTION = (
    "We couldn't find a claim rejection letter in your files. "
    "Please upload the letter or email from your insurer that rejected or cut the claim."
)


class NotARejection(Exception):
    """The uploads don't contain a rejection; stop before the expensive steps."""


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
    has_letter = any(d.doc_type == DocType.REJECTION_LETTER for d in documents)
    if not has_letter and not facts.rejection_reason:
        raise NotARejection(NO_REJECTION)

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

        if not case.title and case.facts:
            case.title = _default_title(case.facts)

        progress("Writing your appeal")
        case.letter = filing.draft_letter(case)

        case.status = CaseStatus.READY
        progress(None)
    except NotARejection as exc:
        case.status = CaseStatus.COLLECTING
        case.progress = str(exc)
        case.events.append(CaseEvent(at=datetime.now(UTC), kind="analysis_failed", text=str(exc)))
        store.save_case(case)
    except Exception as exc:
        log.exception("Analysis failed for case %s", case_id)
        case.status = CaseStatus.COLLECTING
        msg = "We couldn't finish the analysis. Please try again."
        # In local dev surface the real reason so it's self-serve to debug; keep prod copy clean.
        if get_settings().auth_disabled and str(exc):
            msg = f"{msg}\n{exc!s}"
        case.progress = msg
        case.events.append(CaseEvent(at=datetime.now(UTC), kind="analysis_failed", text=msg))
        store.save_case(case)
        raise


def _default_title(facts: CaseFacts) -> str:
    parts = [p for p in (facts.insurer, facts.diagnosis) if p]
    return " · ".join(parts) if parts else "Claim"
