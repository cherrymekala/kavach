"""Intake agent: label each document and extract case facts with Gemini."""

import re

from ..config import get_settings
from ..models import IntakeResult
from . import llm, prompts

_EXCLUSION_REF = re.compile(r"excl", re.IGNORECASE)


def run(document_uris: list[str]) -> IntakeResult:
    result = llm.structured(
        prompts.INTAKE, document_uris, IntakeResult, model=get_settings().model_fast
    )
    facts = result.facts
    # The fast model tends to copy exclusion refs ("Excl02") into rejection_code despite the prompt.
    code = facts.rejection_code
    if code and (_EXCLUSION_REF.search(code) or code == facts.cited_clause):
        facts.rejection_code = None
    return result
