import base64
import uuid

import pytest
from fastapi.testclient import TestClient

from kavach.agents import appeal_mail
from kavach.config import get_settings
from kavach.main import app
from kavach.models import Case, CaseFacts, CaseStatus, Complainant, Letter
from kavach.tools import mail, packs, store

TOKEN = {"X-Kavach-Token": "inbound-secret"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MAIL_INBOUND_TOKEN", "inbound-secret")
    monkeypatch.setenv("MAIL_REPLY_TO", "appeals@kavach.example")
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()


@pytest.fixture
def outbox(monkeypatch):
    sent = []

    def fake_send(to, subject, text, **kw):
        sent.append({"to": to, "subject": subject, "text": text, **kw})
        return f"<msg-{len(sent)}@cloudflare.example>"

    monkeypatch.setattr(mail, "send", fake_send)
    return sent


def _case(
    english: str = "Dear Sir,\nI appeal the rejection.", email: str | None = "lakshmi@example.com"
) -> Case:
    case = Case(
        id=uuid.uuid4().hex,
        owner="dev-user",
        country="IN",
        status=CaseStatus.READY,
        facts=CaseFacts(insurer="STAR HEALTH AND ALLIED INSURANCE CO. LTD.", claim_amount=184000),
        letter=Letter(subject="Appeal against rejection of claim CLI/1", english=english),
        complainant=Complainant(name="Lakshmi Iyer", email=email),
    )
    store.save_case(case)
    return case


def test_unfilled_blanks_and_missing_email_block_sending(client, outbox):
    case = _case(english="Dear Sir,\n[Your Address]\nI appeal.", email=None)
    preview = client.get(f"/cases/{case.id}/send-appeal").json()
    assert {"letter_blanks", "email"} <= set(preview["missing"])
    assert preview["blanks"] == ["[Your Address]"]
    r = client.post(f"/cases/{case.id}/send-appeal", json={"to": "gro@insurer.example"})
    assert r.status_code == 409 and outbox == []


def test_sending_emails_the_letter_and_starts_the_reply_clock(client, outbox):
    case = _case()
    r = client.post(f"/cases/{case.id}/send-appeal", json={"to": "gro@insurer.example"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "filed" and body["next_deadline"]
    assert [e["kind"] for e in body["events"]] == ["emailed", "filed"]
    assert body["complainant"]["insurer_email"] == "gro@insurer.example"

    [msg] = outbox
    assert msg["to"] == "gro@insurer.example" and msg["cc"] == "lakshmi@example.com"
    assert msg["reply_to"] == "appeals@kavach.example"
    assert "I appeal the rejection." in msg["text"]
    assert (
        msg["attachments"][0][0] == "appeal-letter.pdf" and msg["attachments"][0][1][:4] == b"%PDF"
    )
    assert store.case_for_message("<msg-1@cloudflare.example>") == case.id

    again = client.post(f"/cases/{case.id}/send-appeal", json={"to": "gro@insurer.example"})
    assert again.status_code == 409 and len(outbox) == 1


def test_insurer_reply_finds_its_case_by_thread_and_lands_on_the_tracker(
    client, outbox, monkeypatch
):
    case = _case()
    client.post(f"/cases/{case.id}/send-appeal", json={"to": "gro@insurer.example"})
    monkeypatch.setattr(
        appeal_mail,
        "read_reply",
        lambda subject, text: appeal_mail.ReplyRead(
            outcome="needs_documents", summary="They ask for your ultrasound report."
        ),
    )
    payload = {
        "from": "gro@insurer.example",
        "subject": "Re: Appeal against rejection of claim CLI/1",
        "text": "Please share the ultrasound report dated 05/07/2026.",
        "in_reply_to": "<msg-1@cloudflare.example>",
        "references": "<older@insurer.example> <msg-1@cloudflare.example>",
        "attachments": [
            {
                "filename": "query.pdf",
                "content": base64.b64encode(b"%PDF-1.4 query").decode(),
                "type": "application/pdf",
            }
        ],
    }
    assert (
        client.post("/mail/inbound", json=payload, headers={"X-Kavach-Token": "wrong"}).status_code
        == 403
    )
    assert client.post("/mail/inbound", json=payload, headers=TOKEN).json() == {
        "ok": True,
        "matched": True,
    }

    saved = store.load_case(case.id)
    event = saved.events[-1]
    assert event.kind == "insurer_reply" and "ultrasound report" in event.text
    assert saved.documents[-1].filename == "insurer-query.pdf"
    forward = outbox[-1]
    assert forward["to"] == "lakshmi@example.com" and "ultrasound report dated" in forward["text"]


def test_replies_that_answer_no_appeal_are_ignored(client):
    case = _case()
    payload = {
        "from": "spam@example.org",
        "subject": "Hello",
        "in_reply_to": "<unknown@example.org>",
    }
    assert client.post("/mail/inbound", json=payload, headers=TOKEN).json() == {
        "ok": True,
        "matched": False,
    }
    assert store.load_case(case.id).events == []


def test_insurer_directory_matches_the_name_on_the_letter(monkeypatch):
    contacts = [
        {
            "name": "Star Health and Allied Insurance",
            "aliases": [],
            "email": "gro@starhealth.example",
        }
    ]
    monkeypatch.setattr(packs, "load", lambda country: {"insurer_contacts": contacts})
    assert (
        packs.insurer_contact("IN", "STAR HEALTH AND ALLIED INSURANCE CO. LTD.")["email"]
        == "gro@starhealth.example"
    )
    assert packs.insurer_contact("IN", "Niva Bupa") is None


def test_the_placeholder_token_keeps_sending_a_dry_run(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_EMAIL_TOKEN", "unset")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc")
    monkeypatch.setenv("MAIL_FROM", "Kavach <appeals@kavach.example>")
    get_settings.cache_clear()
    assert not mail.configured()
    assert mail.send("gro@insurer.example", "Appeal", "text").startswith("<dry-run-")


def test_cloudflare_request_matches_the_documented_rest_schema(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_EMAIL_TOKEN", "cf-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc123")
    monkeypatch.setenv("MAIL_FROM", "Kavach Appeals <appeals@kavach.example>")
    get_settings.cache_clear()
    calls = []

    class Response:
        status_code = 200

        def json(self):
            return {
                "success": True,
                "errors": [],
                "result": {"message_id": "<abc@cf>", "permanent_bounces": []},
            }

    def fake_post(url, json, headers, timeout):
        calls.append((url, json, headers))
        return Response()

    monkeypatch.setattr(mail.httpx, "post", fake_post)
    mid = mail.send(
        "gro@insurer.example",
        "Appeal",
        "Dear Sir",
        cc="me@example.com",
        reply_to="appeals@kavach.example",
        attachments=[("appeal-letter.pdf", b"%PDF", "application/pdf")],
    )
    url, body, headers = calls[0]
    assert mid == "<abc@cf>"
    assert url == "https://api.cloudflare.com/client/v4/accounts/acc123/email/sending/send"
    assert headers == {"Authorization": "Bearer cf-token"}
    assert body["from"] == {"address": "appeals@kavach.example", "name": "Kavach Appeals"}
    assert body["to"] == ["gro@insurer.example"] and body["cc"] == ["me@example.com"]
    assert body["reply_to"] == "appeals@kavach.example"
    assert body["attachments"][0] == {
        "content": "JVBERg==",
        "filename": "appeal-letter.pdf",
        "type": "application/pdf",
        "disposition": "attachment",
    }
