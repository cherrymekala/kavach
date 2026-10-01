"""Case strategist: arguments, chances and missing documents."""
from ..models import Assessment, CaseFacts
from ..tools import rulings
from . import llm, prompts


def assess(facts: CaseFacts, policy_uri: str, sections: list[dict], country: str) -> Assessment:
    similar = rulings.search_similar(facts, country)
    context = {"facts": facts.model_dump(mode="json"), "regulations": sections, "rulings": similar}
    return llm.structured(prompts.STRATEGIST, [policy_uri], Assessment, context=context)
