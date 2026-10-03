"""Code decoder: exact lookup of TPA/insurer rejection codes from the country pack."""

from ..tools import packs


def decode(country: str, tpa: str | None, code: str | None) -> dict | None:
    if not code:
        return None
    table = packs.load(country).get("rejection_codes", {})
    return table.get(f"{tpa}:{code}") or table.get(code)
