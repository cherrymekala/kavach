"""Runs the pipeline for one case and writes progress to Firestore as it goes.

Kept as plain Python for the MVP so each step is easy to debug. Week 2: wrap the
steps as ADK tools under one root agent (see adk_agent.py) for the demo and pitch.
"""
from ..models import CaseStatus, DocType
from ..tools import store
from . import checker, code_decoder, filing, intake, policy_rules, strategist


def _progress(case, text):
    case.progress = text
    store.save_case(case)


def run_case(case_id: str) -> None:
    case = store.load_case(case_id)
    try:
        _progress(case, "Reading your documents")
        result = intake.run([d.gcs_uri for d in case.documents])
        for label in result.documents:
            if 0 <= label.index < len(case.documents):
                case.documents[label.index].doc_type = label.doc_type
                case.documents[label.index].warning = label.warning
        case.facts = result.facts

        _progress(case, "Decoding the rejection")
        decoded = code_decoder.decode(case.country, case.facts.tpa, case.facts.rejection_code)
        if decoded:
            # An exact code match beats the model's reading of the letter.
            case.facts.rejection_category = decoded["category"]
            if not case.facts.rejection_reason:
                case.facts.rejection_reason = decoded.get("meaning")

        _progress(case, "Finding the rules that apply")
        sections = policy_rules.find_sections(case.country, policy_rules.describe(case.facts))

        _progress(case, "Building your case")
        policy = next((d for d in case.documents if d.doc_type == DocType.POLICY), case.documents[0])
        assessment = strategist.assess(case.facts, policy.gcs_uri, sections, case.country)

        _progress(case, "Checking every source")
        case.assessment = checker.verify(assessment, source_texts={})  # TODO: pass source texts

        _progress(case, "Writing your appeal")
        case.letter = filing.draft_letter(case)

        case.status = CaseStatus.READY
        _progress(case, None)
    except Exception:
        case.status = CaseStatus.COLLECTING
        _progress(case, "We couldn't finish the analysis. Please try again.")
        raise
