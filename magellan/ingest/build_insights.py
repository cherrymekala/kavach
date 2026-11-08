"""Rejection-pattern report: how often patients win at the Ombudsman, by ground, insurer and year.

Reads magellan/sources/rulings.jsonl + rulings_labels.jsonl (the same labelled awards that are in
Vertex AI Search) and writes magellan/packs/IN.insights.json, which GET /insights/IN serves.
Rulings labelled "other" (withdrawn, not maintainable, unclear) are left out.
Run from the repo root:
    python magellan/ingest/build_insights.py
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"
OUT = ROOT / "packs" / "IN.insights.json"

DECISIONS = ("allowed", "partly_allowed", "dismissed")
MIN_CATEGORY = 20  # smaller groups make percentages meaningless
MIN_INSURER = 30
MIN_YEAR = 30
# Within one insurer's scorecard: smaller groups are left out rather than shown as noisy rates.
MIN_SCORECARD_GROUP = 10
# Insurers renamed since the awards were published (name in the awards -> current name).
NOW_KNOWN_AS = {"Reliance General": "IndusInd General Insurance"}


def _records() -> list[dict]:
    labels = {}
    for line in (SOURCES / "rulings_labels.jsonl").open(encoding="utf-8"):
        label = json.loads(line)
        labels[label["id"]] = label
    out = []
    for line in (SOURCES / "rulings.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        label = labels.get(r["id"])
        if not label or label["decision"] not in DECISIONS:
            continue
        year = (r.get("award_date") or "")[:4]
        out.append(
            {
                "decision": label["decision"],
                "category": label["category"],
                "insurer": r.get("insurer"),
                "year": year if year.startswith("20") else None,
            }
        )
    return out


def _row(key: str, counts: Counter) -> dict:
    total = sum(counts.values())
    won = counts["allowed"] + counts["partly_allowed"]
    return {
        "key": key,
        "total": total,
        "allowed": counts["allowed"],
        "partly_allowed": counts["partly_allowed"],
        "dismissed": counts["dismissed"],
        "won_pct": round(100 * won / total) if total else 0,
    }


def _group(records: list[dict], field: str, minimum: int) -> list[dict]:
    groups: dict[str, Counter] = defaultdict(Counter)
    for r in records:
        if r[field] and r[field] != "other":
            groups[r[field]][r["decision"]] += 1
    rows = [_row(k, c) for k, c in groups.items() if sum(c.values()) >= minimum]
    return rows


def _slug(name: str) -> str:
    return "-".join("".join(ch if ch.isalnum() else " " for ch in name.lower()).split())


def _scorecards(records: list[dict], by_category: list[dict]) -> list[dict]:
    """One card per insurer with enough awards: its grounds, how patients fared, and the trend."""
    everyone = {r["key"]: r["won_pct"] for r in by_category}
    totals = Counter(r["insurer"] for r in records if r["insurer"])
    cards = []
    for insurer, total in totals.most_common():
        if total < MIN_INSURER:
            continue
        mine = [r for r in records if r["insurer"] == insurer]
        years = sorted(r["year"] for r in mine if r["year"])
        grounds = sorted(_group(mine, "category", MIN_SCORECARD_GROUP), key=lambda r: -r["total"])
        cards.append(
            {
                **_row(insurer, Counter(r["decision"] for r in mine)),
                "slug": _slug(insurer),
                "now_known_as": NOW_KNOWN_AS.get(insurer),
                "period": {"from": years[0], "to": years[-1]} if years else None,
                "grounds": [
                    {
                        **g,
                        "share_pct": round(100 * g["total"] / total),
                        "everyone_won_pct": everyone.get(g["key"]),
                    }
                    for g in grounds
                ],
                "by_year": sorted(_group(mine, "year", MIN_SCORECARD_GROUP), key=lambda r: r["key"]),
            }
        )
    return cards


def build() -> dict:
    records = _records()
    years = sorted(r["year"] for r in records if r["year"])
    by_category = sorted(_group(records, "category", MIN_CATEGORY), key=lambda r: -r["won_pct"])
    by_insurer = sorted(_group(records, "insurer", MIN_INSURER), key=lambda r: -r["total"])
    by_year = sorted(_group(records, "year", MIN_YEAR), key=lambda r: r["key"])
    return {
        "country": "IN",
        "source": "Insurance Ombudsman award synopses (health and group mediclaim), "
        "published by the Council for Insurance Ombudsmen",
        "period": {"from": years[0], "to": years[-1]},
        "overall": _row("all", Counter(r["decision"] for r in records)),
        "by_category": by_category,
        "by_insurer": by_insurer,
        "by_year": by_year,
        "insurers": _scorecards(records, by_category),
        "note": "Published awards only, mostly 2005-2013; complaints settled earlier never reach "
        "an award. Rates show how disputes that reached the Ombudsman ended, not how often "
        "insurers reject claims.",
    }


if __name__ == "__main__":
    report = build()
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    o = report["overall"]
    print(f"{o['total']} awards, patients won {o['won_pct']}% -> {OUT.relative_to(ROOT.parent)}")
    for r in report["by_category"]:
        print(f"  {r['key']:<26} {r['won_pct']:>3}% of {r['total']}")
