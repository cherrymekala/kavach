"""Label FIDReC insurance case studies with Gemini and add them to the rulings data store (country SG).

Needs magellan/sources/sg/fidrec/case_studies.json (see build steps in magellan/README.md).
Run from the repo root:  USE_VERTEX=true sombrero/.venv/bin/python magellan/ingest/load_fidrec.py
"""

import json
from pathlib import Path

from load_rulings import import_records
from pydantic import BaseModel

from kavach.agents import llm
from kavach.config import get_settings
from kavach.models import RejectionCategory

SOURCES = Path(__file__).resolve().parents[1] / "sources" / "sg" / "fidrec"

PROMPT = """You label Singapore FIDReC case studies (anonymised dispute summaries).
For the case return:
- insurance: true only if it is an insurance claim dispute (health, hospital, surgical,
  critical illness, personal accident, life, travel); false for banking, scams, investments.
- insurer_type: e.g. "health insurer", "travel insurer" (FIDReC does not name firms).
- decision: "allowed" (consumer got what they claimed), "partly_allowed" (partial payment or
  goodwill settlement), "dismissed" (insurer's position upheld), or "other".
- category: the insurer's main ground for rejecting or cutting the claim.
- diagnosis: the illness, injury or event in a few plain words (null if none).
- summary: one sentence: what the insurer did, why, and how FIDReC resolved it and why.
Use only what the case says."""


class _Label(BaseModel):
    insurance: bool
    insurer_type: str | None
    decision: str
    category: RejectionCategory
    diagnosis: str | None
    summary: str


def main() -> None:
    cases = json.loads((SOURCES / "case_studies.json").read_text(encoding="utf-8"))
    records = []
    for c in cases:
        title = " ".join(c["title"].split())
        label = llm.structured(
            PROMPT,
            [],
            _Label,
            context={"title": title, "text": c["text"]},
            model=get_settings().model_fast,
        )
        print(
            f"{'✓' if label.insurance else '·'} {title[:70]:<70} {label.decision:<15} {label.category}"
        )
        if not label.insurance or label.decision == "other":
            continue
        records.append(
            {
                "id": f"sg-fidrec-{c['ka'].lower()}",
                "country": "SG",
                "source": c["url"],
                "case_no": title.split(" ", 3)[2] if title.startswith("Case Study #") else None,
                "insurer": label.insurer_type,
                "decision": label.decision,
                "category": label.category.value,
                "diagnosis": label.diagnosis,
                "summary": label.summary,
                "text": f"FIDReC {title}. {c['text']}",
            }
        )
    print(f"{len(records)} insurance case studies to import")
    import_records(records, update_schema=False)


if __name__ == "__main__":
    main()
