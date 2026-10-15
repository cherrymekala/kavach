from kavach.agents import orchestrator
from kavach.models import Assessment, Case, CaseFacts, CaseStatus, DocLabel, Document, IntakeResult
from kavach.tools import store


def test_irrelevant_uploads_stop_before_the_expensive_steps(monkeypatch):
    result = IntakeResult(documents=[DocLabel(index=0, doc_type="other")], facts=CaseFacts())
    monkeypatch.setattr(orchestrator.intake, "run", lambda uris: result)
    called = []
    monkeypatch.setattr(orchestrator.policy_rules, "find_sections", lambda *a: called.append(1))
    saved = {}
    case = Case(id="x", owner="u", documents=[Document(id="d", filename="cat.jpg", gcs_uri="x")])
    monkeypatch.setattr(store, "load_case", lambda _id: case)
    monkeypatch.setattr(
        store, "save_case", lambda c: saved.update(status=c.status, progress=c.progress)
    )

    orchestrator.run_case("x")

    assert saved == {"status": CaseStatus.COLLECTING, "progress": orchestrator.NO_REJECTION}
    assert not called and case.documents[0].doc_type == "other"


def test_analysis_replaces_auto_title_but_not_typed(monkeypatch):
    facts = CaseFacts(insurer="Star Health", diagnosis="Gallstones")
    result = orchestrator.Analysis(
        facts=facts,
        sections=[],
        similar=[],
        draft=Assessment(strength="weak", score=0.4),
        assessment=Assessment(strength="weak", score=0.4),
    )
    monkeypatch.setattr(orchestrator, "analyse", lambda *a, **k: result)
    monkeypatch.setattr(orchestrator.filing, "draft_letter", lambda c: None)
    monkeypatch.setattr(store, "save_case", lambda c: None)

    # An auto-derived title (from the patient's first message) is upgraded.
    auto = Case(id="a", owner="u", title="hi", title_auto=True)
    monkeypatch.setattr(store, "load_case", lambda _id: auto)
    orchestrator.run_case("a")
    assert auto.title == "Star Health · Gallstones"
    assert auto.title_auto is False

    # A title the patient typed is never overwritten.
    typed = Case(id="b", owner="u", title="My typed title", title_auto=False)
    monkeypatch.setattr(store, "load_case", lambda _id: typed)
    orchestrator.run_case("b")
    assert typed.title == "My typed title"
    assert typed.title_auto is False
