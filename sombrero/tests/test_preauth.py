import pytest

from kavach.agents import intake, llm, policy_rules, preauth
from kavach.models import (
    CaseFacts,
    DocLabel,
    DocType,
    Document,
    IntakeResult,
    PreauthAction,
    Source,
)

PARA_15 = "Health Master Circular 2024, Ch. I, para 15"
ONE_HOUR = "Insurer shall decide on the request for cashless authorization immediately but not more than one hour of receipt of request."


def _docs(tmp_path) -> list[Document]:
    letter = tmp_path / "refusal.txt"
    letter.write_text("Cashless DENIED. Reason: suspected pre-existing disease.")
    return [Document(id="0", filename="refusal.txt", gcs_uri=str(letter))]


@pytest.fixture
def fakes(monkeypatch):
    seen = {}

    def fake_intake(uris):
        return IntakeResult(
            documents=[DocLabel(index=0, doc_type=DocType.REJECTION_LETTER)],
            facts=CaseFacts(
                insurer="STAR HEALTH AND ALLIED INSURANCE CO. LTD.",
                rejection_reason="suspected PED",
            ),
        )

    def fake_llm(prompt, uris, schema, context=None, model=None):
        seen["context"] = context
        return schema(
            status="denied",
            summary="Cashless was refused as a suspected pre-existing disease.",
            actions=[
                PreauthAction(who="hospital", step="Ask the desk for the refusal in writing."),
                PreauthAction(
                    who="hospital",
                    step="Resubmit and ask for a decision within one hour.",
                    sources=[Source(kind="regulation", ref=PARA_15, quote=ONE_HOUR)],
                ),
            ],
            doctor_note="To the TPA: [date first diagnosed].",
            request="Please reconsider.",
            fallback="Pay, keep the bills and claim reimbursement.",
            rules=[
                Source(kind="regulation", ref=PARA_15, quote=ONE_HOUR),
                Source(kind="regulation", ref=PARA_15, quote=ONE_HOUR),
                Source(
                    kind="regulation", ref=PARA_15, quote="Insurers must approve every request."
                ),
            ],
        )

    monkeypatch.setattr(intake, "run", fake_intake)
    monkeypatch.setattr(llm, "structured", fake_llm)
    monkeypatch.setattr(policy_rules, "find_sections", lambda country, question: [])
    return seen


def test_plan_keeps_practical_steps_and_only_verified_rules(tmp_path, fakes):
    _, plan = preauth.check(_docs(tmp_path), "IN")
    assert plan.status == "denied"
    assert plan.actions[0].step == "Ask the desk for the refusal in writing."
    assert plan.actions[1].sources[0].ref == PARA_15  # the real para 15 text contains the quote
    assert [r.ref for r in plan.rules] == [
        PARA_15
    ]  # the invented quote is gone, the duplicate merged
    # The cashless rules from the pack are always in front of the model, with the official contact.
    refs = [s["ref"] for s in fakes["context"]["regulations"]]
    assert PARA_15 in refs and "Health Master Circular 2024, Ch. I, para 16" in refs
    assert fakes["context"]["insurer_contact"]["email"] == "gro@starhealth.in"


def test_uploads_without_a_refusal_stop_early(tmp_path, monkeypatch):
    monkeypatch.setattr(
        intake,
        "run",
        lambda uris: IntakeResult(
            documents=[DocLabel(index=0, doc_type=DocType.BILL)], facts=CaseFacts()
        ),
    )
    with pytest.raises(preauth.NotEnoughDocuments):
        preauth.check(_docs(tmp_path), "IN")
