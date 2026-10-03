"""Fetch the current Insurance Ombudsman offices from cioins.co.in into packs/IN.json.

Run from the repo root:  python3 magellan/ingest/build_in_ombudsman_offices.py
"""

import html
import json
import re
import urllib.request
from pathlib import Path

PACK = Path(__file__).resolve().parents[2] / "magellan" / "packs" / "IN.json"
URL = "https://www.cioins.co.in/Ombudsman"


def _text() -> str:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="ignore")
    raw = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"<(br|/tr|/p|/div|/li|/td)[^>]*>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _field(block: list[str], prefix: str) -> str:
    for line in block:
        if line.lower().startswith(prefix):
            return re.sub(rf"(?i)^{prefix}\.?\s*:?\s*", "", line)
    return ""


def offices() -> list[dict]:
    lines = _text().splitlines()
    out = []
    for i, line in enumerate(lines):
        if line != "Insurance Ombudsman" or i < 2:
            continue
        centre = lines[i - 2].title()
        block = []
        for nxt in lines[i + 1 :]:
            block.append(nxt)
            if nxt.lower().startswith("jurisdiction"):
                break
        address = [b for b in block if not re.match(r"(?i)(tel|email|jurisdiction)", b)]
        out.append(
            {
                "centre": centre,
                "address": ", ".join(a.rstrip(",") for a in address),
                "phone": _field(block, "tel"),
                "email": _field(block, "email"),
                "jurisdiction": _field(block, "jurisdiction"),
            }
        )
    return out


def main() -> None:
    # The page lists every centre twice; the second copy is an older table with clipped text.
    found = list({o["centre"]: o for o in reversed(offices())}.values())[::-1]
    pack = json.loads(PACK.read_text(encoding="utf-8"))
    pack["ombudsman_offices"] = found
    PACK.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for o in found:
        print(f"{o['centre']:<12} {o['email']:<28} {o['jurisdiction'][:70]}")
    print(len(found), "offices")


if __name__ == "__main__":
    main()
