"""Policy and rules agent.

Policy: the whole document goes to Gemini (it fits in context) so clause references stay exact.
Regulations: tree search. Gemini reads only the outline (refs + titles), picks branches, and we
return the verbatim text of the chosen sections.
"""

import json

from pydantic import BaseModel

from ..config import get_settings
from ..tools import packs
from . import llm, prompts

MAX_SECTIONS = 4


class _Picked(BaseModel):
    refs: list[str]


def regulation_outline(country: str) -> list[dict]:
    return packs.load(country).get("regulations", [])


def _leaves(nodes: list[dict]) -> list[dict]:
    out = []
    for n in nodes:
        if n.get("children"):
            out += _leaves(n["children"])
        elif n.get("text"):
            out.append(n)
    return out


def _outline_view(nodes: list[dict], depth: int = 0) -> list[str]:
    lines = []
    for n in nodes:
        label = f"{n['ref']} — {n['title']}" if n.get("title") else n["ref"]
        lines.append("  " * depth + label)
        lines += _outline_view(n.get("children", []), depth + 1)
    return lines


def find_sections(country: str, question: str) -> list[dict]:
    outline = regulation_outline(country)
    leaves = {n["ref"]: n for n in _leaves(outline)}
    if not leaves or not question:
        return []
    picked = llm.structured(
        prompts.RULES_PICK,
        [],
        _Picked,
        context={"rejection": question, "outline": "\n".join(_outline_view(outline))},
        model=get_settings().model_fast,
    )
    refs = [r.split(" — ")[0].strip() for r in picked.refs]  # model often echoes the title too
    refs = [r for r in dict.fromkeys(refs) if r in leaves][:MAX_SECTIONS]
    return [{"ref": r, "title": leaves[r].get("title"), "text": leaves[r]["text"]} for r in refs]


def months_of_cover(facts) -> int | None:
    if not (facts.policy_start and facts.admission_date):
        return None
    start, end = facts.policy_start, facts.admission_date
    return (end.year - start.year) * 12 + end.month - start.month - (end.day < start.day)


def describe(facts) -> str:
    """Question for the tree search, built from intake facts."""
    return json.dumps(
        {
            "category": facts.rejection_category,
            "reason": facts.rejection_reason,
            "cited_clause": facts.cited_clause,
            "diagnosis": facts.diagnosis,
            "months_of_continuous_cover": months_of_cover(facts),
        },
        default=str,
    )
