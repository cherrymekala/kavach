"""Kavach's agents, wrapped for agentgauge: each takes a whirlpool case id and returns JSON.

agentgauge runs every case several times, records the pipeline stages as tool calls and the
Gemini token use (via kavach.agents.llm._track), then gates on accuracy, flakiness and cost.
Run from the repo root with sombrero's venv; see whirlpool/gauge/README.md.
"""

import json
import os
import time
from pathlib import Path

from agentgauge import record_tool, register, register_price
from agentgauge.types import AssertionResult
from google.genai.errors import ClientError

from kavach.agents import intake, orchestrator
from kavach.config import get_settings
from kavach.models import Document

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "whirlpool" / "cases"
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

# USD per 1M tokens. Set these to the current Gemini prices so the cost budget means something:
# GAUGE_PRICE_FAST="in,out" for settings.model_fast, GAUGE_PRICE_REASONING for model_reasoning.
_s = get_settings()
for _model, _env in (
    (_s.model_fast, "GAUGE_PRICE_FAST"),
    (_s.model_reasoning, "GAUGE_PRICE_REASONING"),
):
    if os.environ.get(_env):
        _in, _out = (float(x) for x in os.environ[_env].split(","))
        register_price(_model, _in, _out)


def _case(case_id: str) -> tuple[Path, dict]:
    d = CASES / case_id
    return d, json.loads((d / "case.json").read_text())


def _names(case: dict) -> list[str]:
    return [next(iter(d)) if isinstance(d, dict) else d for d in case["documents"]]


def _files(case_dir: Path, case: dict) -> list[str]:
    return [
        str(ROOT / next(iter(d.values()))) if isinstance(d, dict) else str(case_dir / d)
        for d in case["documents"]
    ]


def _retry(fn):
    # The free AI Studio tier caps input tokens per minute; each policy PDF is ~50k tokens.
    for attempt in range(3):
        try:
            return fn()
        except ClientError as e:
            if e.code != 429 or attempt == 2:
                raise
            time.sleep(60)


def intake_agent(case_id: str) -> str:
    """Intake only: document labels and case facts."""
    case_dir, case = _case(case_id)
    result = _retry(lambda: intake.run(_files(case_dir, case)))
    record_tool("intake", {"documents": len(case["documents"])})
    names = _names(case)
    labels = {names[x.index]: x.doc_type for x in result.documents if 0 <= x.index < len(names)}
    return json.dumps({"facts": result.facts.model_dump(mode="json"), "doc_types": labels})


def full_agent(case_id: str) -> str:
    """The whole pipeline (intake, decoder, rules, similar rulings, strategist, checker).
    Each stage it reports through `progress` is recorded as a tool call, in order."""
    case_dir, case = _case(case_id)
    docs = [
        Document(id=str(i), filename=n, gcs_uri=u)
        for i, (n, u) in enumerate(zip(_names(case), _files(case_dir, case), strict=True))
    ]
    out = _retry(lambda: orchestrator.analyse(docs, case["country"], progress=record_tool))
    a = out.assessment
    kept = sum(len(x.sources) for x in a.arguments)
    drafted = sum(len(x.sources) for x in out.draft.arguments)
    return json.dumps(
        {
            "strength": a.strength,
            "arguments": len(a.arguments),
            "sources_kept": kept,
            "sources_dropped": drafted - kept,
            "missing_documents": a.missing_documents,
            "facts": out.facts.model_dump(mode="json"),
        },
        default=str,
    )


# ---- Kavach-specific checks, registered with agentgauge -------------------------------------


def _norm(v) -> str:
    return "".join(c for c in str(v).lower() if c.isalnum() or c == ".") if v is not None else ""


def _match(field: str, want, got) -> bool:
    """The same matching rules as whirlpool/run_evals.py."""
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


@register("facts_match")
def _facts_match(spec, trace, case, judge):
    """Scores the share of expected fields that match; passes at `min` (default all of them)."""
    got = json.loads(trace.output)
    facts, want = got.get("facts", {}), spec["expected"]
    misses = [f for f in want if not _match(f, want[f], facts.get(f))]
    for name, t in spec.get("doc_types", {}).items():
        if got.get("doc_types", {}).get(name) != t:
            misses.append(f"doc:{name}")
    total = len(want) + len(spec.get("doc_types", {}))
    score = 1 - len(misses) / total if total else 1.0
    detail = ", ".join(
        f"{m}: want {want[m]!r} got {facts.get(m)!r}" if m in want else m for m in misses
    )
    return AssertionResult("facts_match", score >= spec.get("min", 1.0), score, detail)


@register("field_equals")
def _field_equals(spec, trace, case, judge):
    got = json.loads(trace.output).get(spec["field"])
    ok = got == spec["value"]
    return AssertionResult("field_equals", ok, float(ok), "" if ok else f"got {got!r}")
