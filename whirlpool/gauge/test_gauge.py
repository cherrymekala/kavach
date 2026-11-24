"""Offline check of the agentgauge wiring: Gemini is replaced by fakes, so no keys or PDFs needed.
Run: sombrero/.venv/bin/python -m pytest whirlpool/gauge -q"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import agents
import build_suites
from agentgauge import load_suite, run_suite
from agentgauge.tracing import record_llm


def _facts(case_id: str, **override):
    exp = json.loads((agents.CASES / case_id / "case.json").read_text())["expected"]
    d = {f: exp.get(f) for f in agents.FACT_FIELDS} | override
    return NS(model_dump=lambda mode=None: d)


def _labels(case_id: str):
    case = json.loads((agents.CASES / case_id / "case.json").read_text())
    names = agents._names(case)
    return [NS(index=i, doc_type=case["doc_types"][n]) for i, n in enumerate(names)]


@pytest.fixture
def suite(tmp_path):
    p = tmp_path / "intake.yaml"
    import yaml

    p.write_text(yaml.safe_dump(build_suites.intake_suite()))
    return load_suite(p)


def test_perfect_intake_passes(monkeypatch, suite):
    def fake_run(uris):
        cid = Path(uris[0]).parent.name
        record_llm("fake", 50_000, 800)
        return NS(facts=_facts(cid), documents=_labels(cid))

    monkeypatch.setattr(agents.intake, "run", fake_run)
    run = run_suite(suite, agents.intake_agent, workers=2, repeats=2)
    assert run["summary"]["pass_rate"] == 1.0
    assert run["summary"]["tokens_total"] == 2 * len(suite.cases) * 50_800


def test_wrong_clause_and_flake_are_caught(monkeypatch, suite):
    calls = {}

    def fake_run(uris):
        cid = Path(uris[0]).parent.name
        calls[cid] = calls.get(cid, 0) + 1
        bad = cid == "in_004_nondisclosure_niva" and calls[cid] == 2
        return NS(
            facts=_facts(cid, cited_clause="9.9.9") if bad else _facts(cid),
            documents=_labels(cid),
        )

    monkeypatch.setattr(agents.intake, "run", fake_run)
    run = run_suite(suite, agents.intake_agent, workers=1, repeats=3)
    s = run["summary"]
    assert s["flaky_cases"] == ["in_004_nondisclosure_niva"]
    bad = [r for r in run["results"] if not r["passed"]]
    fm = next(a for a in bad[0]["assertions"] if a["kind"] == "facts_match")
    assert len(bad) == 1 and "cited_clause" in fm["detail"]


def test_full_pipeline_records_stages(monkeypatch, tmp_path):
    def fake_analyse(docs, country, progress):
        for s in build_suites.STAGES:
            progress(s)
        a = NS(strength="strong", arguments=[NS(sources=[1, 2])], missing_documents=[])
        return NS(
            assessment=a,
            draft=NS(arguments=[NS(sources=[1, 2, 3])]),
            facts=_facts("in_004_nondisclosure_niva"),
        )

    monkeypatch.setattr(agents.orchestrator, "analyse", fake_analyse)
    out = json.loads(agents.full_agent("in_004_nondisclosure_niva"))
    assert out["strength"] == "strong" and out["sources_dropped"] == 1
