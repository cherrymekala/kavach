"""Country packs: rules, dispute steps, forms and rejection codes per country."""

import json
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
