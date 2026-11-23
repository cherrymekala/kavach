from datetime import date

import pytest
from fastapi.testclient import TestClient

from kavach.agents import intake
from kavach.config import get_settings
from kavach.main import app
from kavach.models import CaseFacts, DocLabel, DocType, IntakeResult, RejectionCategory
from kavach.tools import store


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(store, "_quota", {}, raising=False)
    return TestClient(app)


def _fake(doc_type=DocType.REJECTION_LETTER, reason="Pre-existing disease"):
    def run(paths):
        assert len(paths) == 1
        return IntakeResult(
            documents=[DocLabel(index=0, doc_type=doc_type)],
            facts=CaseFacts(
                insurer="Star Health",
                patient_name="Lakshmi Iyer",
                policy_number="P/123",
                claim_number="CLI/9",
                rejection_date=date(2026, 7, 28),
                claim_amount=184000,
                currency="INR",
                rejection_category=RejectionCategory.PRE_EXISTING if reason else None,
                rejection_reason=reason,
            ),
        )

    return run


def test_signed_out_visitor_gets_the_reason_stats_and_deadline_without_identifiers(
    client, monkeypatch
):
    monkeypatch.setattr(intake, "run", _fake())
    r = client.post(
        "/preview",
        data={"country": "IN"},
        files={"file": ("letter.pdf", b"%PDF-1.4 x", "application/pdf")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_rejection"] and body["rejection_category"] == "pre_existing"
    assert body["guide"]["slug"] == "pre-existing-disease" and body["guide"]["total"] > 0
    assert body["deadline"] == "2027-07-28" and body["deadline_body"] == "Insurance Ombudsman"
    assert body["ladder"][0]["step"] == "Insurer grievance cell"
    flat = r.text
    assert "Lakshmi" not in flat and "P/123" not in flat and "CLI/9" not in flat


def test_pasted_text_works_and_non_letters_are_told_so(client, monkeypatch):
    monkeypatch.setattr(intake, "run", _fake(doc_type=DocType.OTHER, reason=None))
    r = client.post("/preview", data={"text": "Hello, this is my hospital bill."})
    assert r.status_code == 200 and r.json() == {**r.json(), "is_rejection": False, "guide": None}


def test_bad_input_is_refused_before_any_model_call(client, monkeypatch):
    monkeypatch.setattr(intake, "run", lambda p: pytest.fail("model called"))
    assert client.post("/preview", data={"country": "US", "text": "x"}).status_code == 400
    assert client.post("/preview", data={}).status_code == 400
    assert (
        client.post(
            "/preview", files={"file": ("a.exe", b"MZ", "application/octet-stream")}
        ).status_code
        == 415
    )
    assert (
        client.post("/preview", files={"file": ("a.pdf", b"", "application/pdf")}).status_code
        == 400
    )


def test_each_visitor_gets_a_few_checks_a_day(client, monkeypatch):
    monkeypatch.setenv("PREVIEWS_PER_IP_PER_DAY", "2")
    get_settings.cache_clear()
    monkeypatch.setattr(intake, "run", _fake())
    try:
        h = {"x-forwarded-for": "203.0.113.7"}
        codes = [
            client.post("/preview", data={"text": "letter"}, headers=h).status_code
            for _ in range(3)
        ]
        assert codes == [200, 200, 429]
        other = client.post(
            "/preview", data={"text": "letter"}, headers={"x-forwarded-for": "198.51.100.1"}
        )
        assert other.status_code == 200
    finally:
        get_settings.cache_clear()
