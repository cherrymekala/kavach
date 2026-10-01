"""Policy and rules agent.

Policy: the whole document goes to Gemini (it fits in context) so clause references stay exact.
Regulations: tree search. Gemini picks a branch of the section outline, then reads only that section.
"""
from ..tools import packs


def regulation_outline(country: str) -> list[dict]:
    return packs.load(country).get("regulations", [])


def find_sections(country: str, question: str) -> list[dict]:
    # TODO(week 2): let Gemini choose branches from regulation_outline(), then return
    # [{"ref": "Section 3.1(b)", "text": "..."}] for the chosen leaves.
    return []
