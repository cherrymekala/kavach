import pytest

from kavach.agents import discharge
from kavach.models import CaseFacts, DocLabel, Document, IntakeResult, Risk, Source

BILL = "Room rent - Single Private AC (Deluxe) @ Rs. 8,500 x 5 days"
POLICY = "Room, Boarding, Nursing Expenses all-inclusive as provided by the Hospital"


def _docs(tmp_path) -> list[Document]:
    (tmp_path / "bill.txt").write_text(BILL)
    (tmp_path / "policy.txt").write_text(POLICY)
    return [
        Document(id="b", filename="bill.txt", gcs_uri=str(tmp_path / "bill.txt")),
        Document(id="p", filename="policy.txt", gcs_uri=str(tmp_path / "policy.txt")),
    ]


def _intake(types):
    labels = [DocLabel(index=i, doc_type=t) for i, t in enumerate(types)]
    return lambda uris: IntakeResult(documents=labels, facts=CaseFacts(diagnosis="Dengue"))


def test_unsupported_risks_are_dropped_and_verdict_follows_what_is_left(tmp_path, monkeypatch):
    monkeypatch.setattr(discharge.intake, "run", _intake(["bill", "policy"]))
    monkeypatch.setattr(discharge.policy_rules, "find_sections", lambda c, q: [])
    real = Risk(
        title="Room above the limit",
        severity="medium",
        why="Proportionate deduction",
        fix="Move to a standard room",
        sources=[Source(kind="bill", ref="line 1", quote="Single Private AC (Deluxe) @ Rs. 8,500")],
    )
    invented = Risk(
        title="Cataract sub-limit",
        severity="high",
        why="",
        fix="",
        sources=[Source(kind="policy", ref="cl. 3", quote="cataract limited to Rs. 25,000")],
    )
    draft = discharge._Draft(verdict="high_risk", summary="s", risks=[invented, real])
    monkeypatch.setattr(discharge.llm, "structured", lambda *a, **k: draft)
    monkeypatch.setattr(discharge.checker, "_gemini_check", lambda pending, docs: set())

    _, result = discharge.check(_docs(tmp_path), "IN")

    assert [r.title for r in result.risks] == ["Room above the limit"]
    assert result.verdict == "some_risks"  # the only high risk was unsupported
    assert result.risks[0].sources[0].verified


def test_a_policy_and_a_bill_or_summary_are_required(tmp_path, monkeypatch):
    monkeypatch.setattr(discharge.intake, "run", _intake(["bill", "other"]))
    with pytest.raises(discharge.NotEnoughDocuments):
        discharge.check(_docs(tmp_path), "IN")
