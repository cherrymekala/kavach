"""Score the intake agent against whirlpool/cases/*/case.json.

Run from the repo root with sombrero's venv:
    sombrero/.venv/bin/python whirlpool/run_evals.py [--full | --discharge] [case_id ...]
--full runs the whole pipeline (needs Vertex AI Search) and scores the strength verdict.
--discharge runs the pre-discharge check on whirlpool/discharge/ and scores the risks found.
Needs magellan/sources (run magellan/ingest/fetch_sources.sh) and GOOGLE_API_KEY in .env.
"""

import json
import re
import sys
import time
from pathlib import Path

from google.genai.errors import ClientError

from kavach.agents import discharge, intake, orchestrator
from kavach.models import Document

ROOT = Path(__file__).resolve().parents[1]
CASES = Path(__file__).parent / "cases"
DISCHARGE = Path(__file__).parent / "discharge"
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
        files.append(
            str(ROOT / next(iter(d.values()))) if isinstance(d, dict) else str(case_dir / d)
        )
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


def run_full(case_dir: Path) -> bool:
    """Whole pipeline (intake -> checker); scores the strength verdict and prints arguments."""
    case = json.loads((case_dir / "case.json").read_text())
    docs = [
        Document(id=str(i), filename=n, gcs_uri=u)
        for i, (n, u) in enumerate(zip(_names(case), _files(case_dir, case)))
    ]
    out = orchestrator.analyse(docs, case["country"])
    a, want = out.assessment, case["expected"].get("strength")
    dropped = sum(len(x.sources) for x in out.draft.arguments) - sum(
        len(x.sources) for x in a.arguments
    )
    mark = "✓" if a.strength == want else "✗"
    print(
        f"\n{case['id']}: {mark} strength {a.strength} (expected {want}), "
        f"similar won {a.similar_cases_won}/{a.similar_cases_total}, "
        f"arguments {len(a.arguments)}/{len(out.draft.arguments)} kept, {dropped} sources dropped"
    )
    for arg in a.arguments:
        print(f"  • {arg.claim}")
        for src in arg.sources:
            print(f'      [{src.kind}] {src.ref}: "{src.quote[:90]}"')
    if a.missing_documents:
        print(f"  missing: {'; '.join(a.missing_documents)}")
    return a.strength == want


def run_discharge(case_dir: Path) -> bool:
    """Pre-discharge check; passes if the verdict is not the excluded one and every expected
    keyword appears in some verified risk title."""
    case = json.loads((case_dir / "case.json").read_text())
    docs = [
        Document(id=str(i), filename=n, gcs_uri=u)
        for i, (n, u) in enumerate(zip(_names(case), _files(case_dir, case)))
    ]
    _, check = discharge.check(docs, case["country"])
    exp = case["expected"]
    titles = " ".join(r.title.lower() for r in check.risks)
    good = check.verdict != exp.get("verdict_not") and all(
        k in titles for k in exp.get("risk_keywords", [])
    )
    print(f"\n{case['id']}: {'✓' if good else '✗'} {check.verdict}, {len(check.risks)} risks")
    for r in check.risks:
        print(f"  [{r.severity}] {r.title}\n      fix: {r.fix}")
    return good


def main() -> None:
    args = sys.argv[1:]
    full = "--full" in args
    pre = "--discharge" in args
    wanted = {x for x in args if not x.startswith("--")}
    dirs = [
        d
        for d in sorted((DISCHARGE if pre else CASES).iterdir())
        if (d / "case.json").exists() and (not wanted or d.name in wanted)
    ]
    if pre:
        right = sum(run_discharge(d) for d in dirs)
        print(f"\nDischarge checks: {right}/{len(dirs)}")
        return
    if full:
        right = sum(run_full(d) for d in dirs)
        print(f"\nStrength verdicts: {right}/{len(dirs)}")
        return
    ok = total = 0
    for d in dirs:
        a, b = run_case(d)
        ok, total = ok + a, total + b
    print(f"\nIntake accuracy: {ok}/{total} = {ok / max(total, 1):.0%}")


if __name__ == "__main__":
    main()
