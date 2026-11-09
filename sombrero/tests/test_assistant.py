import uuid

from fastapi.testclient import TestClient

from kavach.agents import assistant, llm
from kavach.main import app
from kavach.models import Case
from kavach.tools import store


def test_chat_answers_before_any_upload_and_keeps_the_conversation(monkeypatch):
    calls = []

    def fake_text(system, context, model=None):
        calls.append((system, context))
        return "Hello! Attach your rejection letter and policy, then run the analysis."

    monkeypatch.setattr(llm, "text", fake_text)
    case = Case(id=uuid.uuid4().hex, owner="dev-user", country="IN", language="hi")
    store.save_case(case)
    client = TestClient(app)

    r = client.post(f"/cases/{case.id}/ask", json={"question": "hi, what can you do?"})
    assert r.status_code == 200 and "rejection letter" in r.json()["answer"]
    system, context = calls[0]
    assert system == assistant.BEFORE_ANALYSIS and context["case_language"] == "hi"

    client.post(f"/cases/{case.id}/ask", json={"question": "and after that?"})
    assert [m["who"] for m in calls[1][1]["earlier_messages"]] == ["patient", "kavach"]
    assert [e.kind for e in store.load_case(case.id).events] == ["message", "ask"] * 2
