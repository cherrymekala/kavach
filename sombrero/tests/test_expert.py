import json
import uuid

import pytest
from fastapi.testclient import TestClient

from kavach.agents import expert
from kavach.config import get_settings
from kavach.main import app
from kavach.models import Assessment, Case, CaseFacts, CaseStatus, Complainant, Document
from kavach.tools import mail, store


def _case(strength: str = "strong", amount: float = 184000) -> Case:
    case = Case(
        id=uuid.uuid4().hex,
        owner="dev-user",
        country="IN",
        status=CaseStatus.READY,
        facts=CaseFacts(
            insurer="Star Health", claim_amount=amount, rejection_reason="pre-existing"
        ),
        assessment=Assessment(strength=strength, score=0.5, arguments=[]),
        complainant=Complainant(name="Lakshmi Iyer"),
        documents=[
            Document(id="d", filename="policy.pdf", gcs_uri="gs://bucket/secret/policy.pdf")
        ],
    )
    store.save_case(case)
    return case


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("EXPERT_TEAM_EMAIL", "team@kavach.example")
    get_settings.cache_clear()
    sent = []
    monkeypatch.setattr(
        mail, "send", lambda to, subject, text, **kw: sent.append((to, subject, text)) or "<id>"
    )
    yield TestClient(app), sent
    get_settings.cache_clear()


def test_an_expert_is_suggested_for_weak_or_high_value_cases():
    assert expert.offer_reason(_case(strength="weak")) == "weak"
    assert expert.offer_reason(_case(amount=600000)) == "high_value"  # IN threshold Rs 5 lakh
    assert expert.offer_reason(_case()) is None


def test_consent_and_a_way_to_reach_the_patient_are_required(client):
    c, sent = client
    case = _case(strength="weak")
    url = f"/cases/{case.id}/expert"
    assert c.post(url, json={"consent": False, "phone": "+91 99999 00001"}).status_code == 422
    assert c.post(url, json={"consent": True}).status_code == 422
    assert sent == [] and store.load_case(case.id).expert_requested_at is None


def test_a_request_queues_a_summary_without_documents_and_tells_the_team(client):
    c, sent = client
    case = _case(strength="weak")
    offer = c.get(f"/cases/{case.id}/expert").json()
    assert offer["reason"] == "weak" and offer["requested_at"] is None and offer["shared"]

    r = c.post(
        f"/cases/{case.id}/expert",
        json={"consent": True, "phone": "+91 99999 00001", "note": "Please call after 6 pm."},
    )
    assert r.status_code == 200
    assert r.json()["expert_requested_at"] and r.json()["events"][-1]["kind"] == "expert_requested"

    [queued] = [q for q in store._expert_requests.values() if q["case_id"] == case.id]
    assert (
        queued["reason"] == "weak"
        and queued["phone"] == "+91 99999 00001"
        and queued["status"] == "open"
    )
    assert (
        queued["summary"]["insurer"] == "Star Health"
        and queued["summary"]["patient_name"] == "Lakshmi Iyer"
    )
    assert "gs://" not in json.dumps(queued)  # documents never leave the case

    [(to, subject, text)] = sent
    assert (
        to == "team@kavach.example"
        and "Star Health" in subject
        and "Please call after 6 pm." in text
    )
    assert "gs://" not in text

    assert (
        c.post(f"/cases/{case.id}/expert", json={"consent": True, "phone": "+91 1"}).status_code
        == 409
    )
