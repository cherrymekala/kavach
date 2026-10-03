"""Case strategist: arguments with verbatim sources, a strength verdict and missing documents.

Generation step of the RAG pipeline: Gemini sees the case documents plus the retrieved
regulation sections and similar rulings, and may cite only those.
"""

from pydantic import BaseModel

from ..models import Argument, Assessment, CaseFacts, Document
from . import llm, policy_rules, prompts

WON = ("allowed", "partly_allowed")
SCORE = {"strong": 0.8, "medium": 0.5, "weak": 0.2}


class _Draft(BaseModel):
    strength: str  # strong | medium | weak
    reasoning: str
    arguments: list[Argument]
    missing_documents: list[str]


def _ruling_view(r: dict) -> dict:
    keep = ("id", "decision", "insurer", "award_date", "diagnosis", "summary")
    return {k: r.get(k) for k in keep}


def assess(
    facts: CaseFacts, documents: list[Document], sections: list[dict], similar: list[dict]
) -> Assessment:
    won = sum(1 for r in similar if r.get("decision") in WON)
    context = {
        "facts": facts.model_dump(mode="json"),
        "months_of_continuous_cover": policy_rules.months_of_cover(facts),
        "documents": [
            {"file_index": i, "type": d.doc_type, "name": d.filename}
            for i, d in enumerate(documents)
        ],
        "regulations": sections,
        "similar_rulings": {
            "won_by_patient": won,
            "total": len(similar),
            "cases": [_ruling_view(r) for r in similar],
        },
    }
    draft = llm.structured(
        prompts.STRATEGIST, [d.gcs_uri for d in documents], _Draft, context=context
    )
    strength = draft.strength if draft.strength in SCORE else "medium"
    return Assessment(
        strength=strength,
        score=SCORE[strength],
        arguments=draft.arguments,
        similar_cases_won=won,
        similar_cases_total=len(similar),
        missing_documents=draft.missing_documents,
    )
