"""Country packs: rules, dispute steps, forms and rejection codes per country."""
import json
from functools import lru_cache
from pathlib import Path

from ..config import get_settings


@lru_cache
def load(country: str) -> dict:
    path = Path(get_settings().packs_dir) / f"{country.upper()}.json"
    return json.loads(path.read_text(encoding="utf-8"))
