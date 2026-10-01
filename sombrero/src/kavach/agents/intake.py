"""Intake agent: classify documents and extract case facts with Gemini."""
from ..models import CaseFacts
from . import llm, prompts


def extract_facts(document_uris: list[str]) -> CaseFacts:
    return llm.structured(prompts.INTAKE, document_uris, CaseFacts)
