"""Generate agentgauge suites from whirlpool/cases/*/case.json, so a new case is tested as soon as
its folder exists. Run from the repo root: python whirlpool/gauge/build_suites.py"""

import json
from pathlib import Path

import yaml

HERE = Path(__file__).parent
CASES = HERE.parent / "cases"
FACT_FIELDS = [
    "insurer",
    "tpa",
    "policy_start",
    "admission_date",
    "first_diagnosis_date",
    "claim_amount",
    "currency",
    "rejection_code",
    "rejection_category",
    "cited_clause",
]
STAGES = [
    "Reading your documents",
    "Decoding the rejection",
    "Finding the rules that apply",
    "Looking up similar past cases",
    "Building your case",
    "Checking every source",
]


def _cases() -> list[dict]:
    return [
        json.loads((d / "case.json").read_text())
        for d in sorted(CASES.iterdir())
        if (d / "case.json").exists()
    ]


def intake_suite() -> dict:
    cases = []
    for c in _cases():
        exp = {f: c["expected"].get(f) for f in FACT_FIELDS}
        cases.append(
            {
                "id": c["id"],
                "input": c["id"],
                "tags": [c["country"].lower()],
                "assert": [
                    {"type": "facts_match", "expected": exp, "doc_types": c["doc_types"]},
                    {"type": "tool_called", "name": "intake", "critical": True},
                ],
            }
        )
    return {
        "suite": {
            "name": "kavach-intake",
            "repeats": 3,
            "pass_threshold": 1.0,
            "defaults": [{"type": "max_latency", "seconds": 120}],
        },
        "cases": cases,
    }


def full_suite() -> dict:
    cases = []
    for c in _cases():
        want = c["expected"].get("strength")
        if not want:
            continue
        cases.append(
            {
                "id": c["id"],
                "input": c["id"],
                "tags": [c["country"].lower(), want],
                "assert": [
                    {"type": "field_equals", "field": "strength", "value": want, "weight": 2},
                    {"type": "tool_order", "sequence": STAGES, "critical": True},
                    {"type": "regex", "pattern": r'"arguments": [1-9]'},
                ],
            }
        )
    return {
        "suite": {"name": "kavach-full", "repeats": 2, "pass_threshold": 0.8},
        "cases": cases,
    }


if __name__ == "__main__":
    for name, suite in (("intake.yaml", intake_suite()), ("full.yaml", full_suite())):
        (HERE / name).write_text(yaml.safe_dump(suite, sort_keys=False, allow_unicode=True))
        print(f"wrote whirlpool/gauge/{name}: {len(suite['cases'])} cases")
