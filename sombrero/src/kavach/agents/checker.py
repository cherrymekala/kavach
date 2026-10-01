"""Checker agent: drop any argument whose quote is not in its source."""
from ..models import Assessment


def verify(assessment: Assessment, source_texts: dict[str, str]) -> Assessment:
    kept = []
    for arg in assessment.arguments:
        if all(s.quote and s.quote in source_texts.get(s.kind, "") for s in arg.sources):
            kept.append(arg)
    # TODO(week 2): add a Gemini pass (prompts.CHECKER) for paraphrased quotes.
    return assessment.model_copy(update={"arguments": kept})
