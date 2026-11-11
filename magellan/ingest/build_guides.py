"""Build public, search-friendly guides per rejection reason (magellan/packs/IN.guides.json).

Each guide = the real outcome numbers from published Ombudsman awards, a few short award
summaries (allowed, partly allowed and dismissed, so the picture is honest), the IRDAI rules
that apply (verbatim from IN.json) and the dispute ladder. No new claims are written here:
everything comes from data already checked into the packs or labelled from public awards.

Run: python magellan/ingest/build_guides.py   (needs magellan/sources/, git-ignored)
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACK = json.loads((ROOT / "packs/IN.json").read_text())
INSIGHTS = json.loads((ROOT / "packs/IN.insights.json").read_text())

RULES = {
    "room_rent": ["Standardization MC 2020, Standard Definition 39", "Health Master Circular 2024, Ch. I, para 17"],
    "missing_documents": ["Health Master Circular 2024, Ch. I, para 17"],
    "reasonable_charges": ["Standardization MC 2020, Standard Definition 37"],
    "hospital_ineligible": ["Standardization MC 2020, Standard Definition 16"],
    "late_intimation": ["Standardization MC 2020, Standard Definition 31", "Health Master Circular 2024, Ch. I, para 17"],
    "not_medically_necessary": ["Standardization MC 2020, Standard Definition 27"],
    "sub_limit": ["Health Master Circular 2024, Ch. I, para 17"],
    "pre_existing": ["Products Regulations 2024, Sch. III, cl. 1.6", "Standardization MC 2020, Excl01"],
    "under_24_hours": ["Standardization MC 2020, Standard Definition 17", "Standardization MC 2020, Standard Definition 9"],
    "initial_waiting_period": ["Standardization MC 2020, Excl03"],
    "fraud": ["Health Master Circular 2024, Ch. I, para 13"],
    "specific_waiting_period": ["Products Regulations 2024, Sch. III, cl. 1.7", "Standardization MC 2020, Excl02"],
    "excluded_treatment": ["Standardization MC 2020, Exclusions not allowed"],
    "diagnostic_only": ["Standardization MC 2020, Excl04"],
    "non_disclosure": ["Standardization MC 2020, Standard Definition 12", "Products Regulations 2024, Sch. III, cl. 8"],
}

SLUGS = {
    "room_rent": "room-rent-limit",
    "missing_documents": "missing-documents",
    "reasonable_charges": "charges-not-reasonable",
    "hospital_ineligible": "hospital-not-eligible",
    "late_intimation": "late-intimation",
    "not_medically_necessary": "not-medically-necessary",
    "sub_limit": "sub-limit-reached",
    "pre_existing": "pre-existing-disease",
    "under_24_hours": "hospitalised-under-24-hours",
    "initial_waiting_period": "first-30-days-waiting-period",
    "fraud": "suspected-fraud",
    "specific_waiting_period": "specific-disease-waiting-period",
    "excluded_treatment": "excluded-treatment",
    "diagnostic_only": "admitted-only-for-tests",
    "non_disclosure": "non-disclosure",
}

MAX_RULE_CHARS = 900


def rules_by_ref() -> dict:
    out = {}

    def walk(nodes):
        for n in nodes:
            if "children" in n:
                walk(n["children"])
            else:
                out[n["ref"]] = n

    walk(PACK["regulations"])
    return out


def examples(category: str) -> list[dict]:
    src = ROOT / "sources"
    meta = {}
    for line in (src / "rulings.jsonl").open():
        r = json.loads(line)
        meta[r["id"]] = r
    picked: dict[str, list] = {"allowed": [], "partly_allowed": [], "dismissed": []}
    for line in (src / "rulings_labels.jsonl").open():
        lab = json.loads(line)
        if lab.get("category") != category or lab.get("decision") not in picked:
            continue
        m = meta.get(lab["id"], {})
        summary = (lab.get("summary") or "").strip()
        if not summary or len(summary) > 420:
            continue
        picked[lab["decision"]].append(
            {
                "decision": lab["decision"],
                "summary": summary,
                "insurer": m.get("insurer"),
                "year": (m.get("award_date") or "")[:4] or None,
                "case_no": m.get("case_no"),
            }
        )
    out = []
    for decision, n in (("allowed", 2), ("partly_allowed", 1), ("dismissed", 1)):
        rows = sorted(picked[decision], key=lambda r: r["year"] or "", reverse=True)
        out += rows[:n]
    return out


def main() -> None:
    refs = rules_by_ref()
    guides = []
    for cat in INSIGHTS["by_category"]:
        key = cat["key"]
        rules = []
        for ref in RULES.get(key, []):
            r = refs[ref]
            text = r["text"]
            if len(text) > MAX_RULE_CHARS:
                text = text[:MAX_RULE_CHARS].rsplit(" ", 1)[0] + " …"
            rules.append({"ref": ref, "title": r.get("title"), "text": text})
        guides.append(
            {
                "key": key,
                "slug": SLUGS[key],
                "stats": cat,
                "rules": rules,
                "examples": examples(key),
            }
        )
    out = {
        "country": "IN",
        "source": INSIGHTS["source"],
        "period": INSIGHTS["period"],
        "overall": INSIGHTS["overall"],
        "note": INSIGHTS["note"],
        "ladder": [
            {"step": s["step"], "dispute_body": s["dispute_body"], "deadline_days": s["deadline_days"], "form": s["form"]}
            for s in PACK["dispute_process"]
        ],
        "limitation": PACK["limitation"],
        "guides": guides,
    }
    path = ROOT / "packs/IN.guides.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(guides)} guides → {path} ({sum(len(g['examples']) for g in guides)} example awards)")


if __name__ == "__main__":
    main()
