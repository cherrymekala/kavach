"""Country packs: rules, dispute steps, forms and rejection codes per country."""

import json
import re
from functools import lru_cache
from pathlib import Path

from ..config import REPO_ROOT, get_settings


def _dir() -> Path:
    packs = Path(get_settings().packs_dir)
    if not packs.is_absolute() and not packs.exists():
        packs = REPO_ROOT / packs
    return packs


@lru_cache
def load(country: str) -> dict:
    path = _dir() / f"{country.upper()}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def insights(country: str) -> dict | None:
    """Rejection-pattern report (magellan/ingest/build_insights.py), if built for the country."""
    path = _dir() / f"{country.upper()}.insights.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _norm(name: str) -> str:
    words = re.sub(r"[^a-z0-9 ]+", " ", name.lower()).split()
    noise = {
        "the",
        "co",
        "company",
        "ltd",
        "limited",
        "insurance",
        "general",
        "health",
        "and",
        "pte",
        "berhad",
        "bhd",
    }
    return " ".join(w for w in words if w not in noise)


def insurer_contact(country: str, insurer: str | None) -> dict | None:
    """The insurer's grievance contact from the pack's `insurer_contacts`, matched by name."""
    if not insurer:
        return None
    wanted = _norm(insurer)
    if not wanted:
        return None
    for contact in load(country).get("insurer_contacts", []):
        names = [contact.get("name", ""), *contact.get("aliases", [])]
        for name in names:
            have = _norm(name)
            if have and (
                have == wanted or wanted.startswith(have + " ") or have.startswith(wanted + " ")
            ):
                return contact
    return None
