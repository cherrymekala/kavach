"""Country packs: rules, dispute steps, forms and rejection codes per country."""
import json
from functools import lru_cache
from pathlib import Path

from ..config import REPO_ROOT, get_settings


@lru_cache
def load(country: str) -> dict:
    packs = Path(get_settings().packs_dir)
    if not packs.is_absolute() and not packs.exists():
        packs = REPO_ROOT / packs
    path = packs / f"{country.upper()}.json"
    return json.loads(path.read_text(encoding="utf-8"))
