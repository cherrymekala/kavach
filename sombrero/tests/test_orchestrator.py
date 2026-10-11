from kavach.agents import orchestrator
from kavach.models import Case, CaseFacts, CaseStatus, DocLabel, Document, IntakeResult
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
