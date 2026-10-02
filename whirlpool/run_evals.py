"""Score the intake agent against whirlpool/cases/*/case.json.

Run from the repo root with sombrero's venv:
    sombrero/.venv/bin/python whirlpool/run_evals.py [case_id ...]
Needs magellan/sources (run magellan/ingest/fetch_sources.sh) and GOOGLE_API_KEY in .env.
"""
import json
import re
import sys
import time
from pathlib import Path

from google.genai.errors import ClientError

from kavach.agents import intake

ROOT = Path(__file__).resolve().parents[1]
CASES = Path(__file__).parent / "cases"
FACT_FIELDS = [
    "insurer", "tpa", "policy_start", "admission_date", "first_diagnosis_date",
    "claim_amount", "currency", "rejection_code", "rejection_category", "cited_clause",
]


def _norm(v) -> str:
    return re.sub(r"[^a-z0-9.]", "", str(v).lower()) if v is not None else ""


def _match(field: str, want, got) -> bool:
    if want is None:
        return got is None
    if got is None:
        return False
    if field == "claim_amount":
        return abs(float(want) - float(got)) < 1
    w, g = _norm(want), _norm(got)
    if field in ("insurer", "tpa"):
        return w in g or g in w
    if field == "cited_clause":
        return w in g
    return w == g


def _files(case_dir: Path, case: dict) -> list[str]:
    files = []
    for d in case["documents"]:
        files.append(str(ROOT / next(iter(d.values()))) if isinstance(d, dict) else str(case_dir / d))
    return files


def _names(case: dict) -> list[str]:
    return [next(iter(d)) if isinstance(d, dict) else d for d in case["documents"]]


def run_case(case_dir: Path) -> tuple[int, int]:
    case = json.loads((case_dir / "case.json").read_text())
    for attempt in range(3):
        try:
            result = intake.run(_files(case_dir, case))
            break
        except ClientError as e:
            # Free tier caps input tokens per minute; each policy PDF is ~50k tokens.
            if e.code != 429 or attempt == 2:
                raise
            time.sleep(60)
    got = result.facts.model_dump(mode="json")
    exp = case["expected"]
    ok = total = 0
    print(f"\n{case['id']}")
    for f in FACT_FIELDS:
        good = _match(f, exp.get(f), got.get(f))
        ok, total = ok + good, total + 1
        if not good:
            print(f"  ✗ {f}: expected {exp.get(f)!r}, got {got.get(f)!r}")
    names = _names(case)
    for label in result.documents:
        name = names[label.index] if 0 <= label.index < len(names) else "?"
        good = case["doc_types"].get(name) == label.doc_type
        ok, total = ok + good, total + 1
        if not good:
            print(f"  ✗ doc {name}: expected {case['doc_types'].get(name)}, got {label.doc_type}")
    print(f"  {ok}/{total}")
    return ok, total


def main() -> None:
    wanted = set(sys.argv[1:])
    dirs = [d for d in sorted(CASES.iterdir()) if (d / "case.json").exists() and (not wanted or d.name in wanted)]
    ok = total = 0
    for d in dirs:
        a, b = run_case(d)
        ok, total = ok + a, total + b
    print(f"\nIntake accuracy: {ok}/{total} = {ok / max(total, 1):.0%}")


if __name__ == "__main__":
    main()
