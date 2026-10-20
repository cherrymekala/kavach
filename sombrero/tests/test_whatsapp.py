"""WhatsApp channel: Meta's signature, the commands, media intake and the reminder window.

Nothing here calls Meta or Gemini: outbound sends are captured, and the analysis is stubbed.
The settings cache is cleared around each test, as the other suites do, because `get_settings`
is cached for the life of the process.
"""

import hashlib
import hmac
import json
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from kavach.agents import whatsapp as copy
from kavach.config import get_settings
from kavach.main import app
from kavach.models import Assessment, Case, CaseFacts, CaseStatus, Document, Letter
from kavach.routers import whatsapp as channel
from kavach.tools import accounts, store
from kavach.tools import whatsapp as wa

SECRET = "app-secret"
SENDER = "919493925966"  # +91 …: India


@pytest.fixture
def cfg(monkeypatch):
    """Local mode: auth off, packs found, no Meta credentials."""
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", SECRET)
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "")
    monkeypatch.setenv("WHATSAPP_TEMPLATE", "")
    monkeypatch.setenv("WHATSAPP_DRY_RUN", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def clean(monkeypatch, tmp_path):
    """Fresh in-memory store, upload folder and rate limits for every test."""
    store._memory.clear()
    store._sessions.clear()
    store._seen.clear()
    store._quota.clear()
    monkeypatch.chdir(tmp_path)
    yield


@pytest.fixture
def sent(monkeypatch):
    """Capture what we would have sent, instead of calling Meta."""
    out: list[tuple] = []
    monkeypatch.setattr(wa, "send_text", lambda to, body: out.append(("text", to, body)))
    monkeypatch.setattr(
        wa,
        "send_media",
        lambda to, data, filename, mime, caption=None: out.append(
            ("media", to, filename, data, caption)
        ),
    )
    return out


def _sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _post(payload: dict, secret: str = SECRET):
    body = json.dumps(payload).encode()
    return TestClient(app).post(
        "/whatsapp/webhook", content=body, headers={"X-Hub-Signature-256": _sign(body, secret)}
    )


def _text(body: str, mid: str = "wamid.1", sender: str = SENDER) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": sender,
                                    "id": mid,
                                    "timestamp": "1760000000",
                                    "type": "text",
                                    "text": {"body": body},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


def _case(**kwargs) -> Case:
    case = Case(
        id=kwargs.pop("id", "case-1"),
        owner="dev-user",
        created_at=datetime.now(UTC),
        country="IN",
        **kwargs,
    )
    store.save_case(case)
    return case


def _replies(sent: list[tuple]) -> list[str]:
    return [s[2] for s in sent if s[0] == "text"]


# ── The webhook handshake ─────────────────────────────────────────────────────────────


def test_subscription_challenge_is_echoed(cfg):
    resp = TestClient(app).get(
        "/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "42"},
    )
    assert resp.status_code == 200
    assert resp.text == "42"


def test_subscription_challenge_rejects_a_wrong_verify_token(cfg):
    resp = TestClient(app).get(
        "/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "guess", "hub.challenge": "42"},
    )
    assert resp.status_code == 403


def test_webhook_rejects_a_body_not_signed_with_the_app_secret(cfg, sent):
    resp = _post(_text("status"), secret="not-the-app-secret")
    assert resp.status_code == 403
    assert sent == []  # nothing was processed


def test_webhook_accepts_metas_signature(cfg, sent):
    assert _post(_text("hello")).status_code == 200
    assert sent


def test_signature_helper_rejects_a_missing_header(cfg):
    assert wa.signature_ok(b"{}", None) is False
    assert wa.signature_ok(b"{}", "sha1=abc") is False


# ── Who is talking ────────────────────────────────────────────────────────────────────


def test_unknown_number_is_asked_to_sign_in_first(cfg, sent, monkeypatch):
    monkeypatch.setattr(accounts, "uid_for_phone", lambda phone: None)
    _post(_text("status"))
    assert len(sent) == 1
    assert "Sign in to Kavach with this same phone number" in _replies(sent)[0]


def test_whatsapp_digits_become_an_e164_number():
    assert accounts.to_e164("919493925966") == "+919493925966"
    assert accounts.to_e164("+91 94939 25966") == "+919493925966"
    assert accounts.to_e164("") == ""


def test_country_follows_the_dialling_code():
    assert [channel.copy.country_for_phone(p) for p in ("+9194", "+6591", "+6012")] == [
        "IN",
        "SG",
        "MY",
    ]


def test_first_reply_explains_what_to_send(cfg, sent):
    _post(_text("hi"))
    assert "Send me the documents" in _replies(sent)[0]


# ── Commands ──────────────────────────────────────────────────────────────────────────


def test_status_reports_the_next_deadline(cfg, sent):
    deadline = datetime.now(UTC) + timedelta(days=12)
    _case(status=CaseStatus.FILED, next_deadline=deadline, facts=CaseFacts(insurer="Star Health"))
    _post(_text("status"))
    reply = _replies(sent)[0]
    assert "Star Health" in reply
    assert deadline.strftime("%d %b %Y") in reply
    assert "12 days left" in reply


def test_status_shows_the_disclaimer_next_to_the_assessment(cfg, sent):
    case = _case(status=CaseStatus.READY)
    case.assessment = Assessment(strength="strong", score=0.8)
    store.save_case(case)
    _post(_text("status"))
    assert "not legal advice" in _replies(sent)[0]


def test_question_before_analysis_is_deferred(cfg, sent):
    _case(status=CaseStatus.COLLECTING)
    _post(_text("why was my claim rejected?"))
    assert "reply *ANALYSE*" in _replies(sent)[0]


def test_delete_needs_a_confirmation(cfg, sent):
    _case()
    _post(_text("delete"))
    assert "Reply *DELETE YES*" in _replies(sent)[0]
    assert store.load_case("case-1") is not None

    _post(_text("DELETE YES", mid="wamid.2"))
    assert store.load_case("case-1") is None


def test_stop_keeps_the_channel_quiet(cfg, sent):
    _case(status=CaseStatus.READY)
    _post(_text("stop"))
    assert "won't message you" in _replies(sent)[0]

    _post(_text("status", mid="wamid.2"))
    assert len(_replies(sent)) == 1  # muted, so no reply to a normal command


def test_cases_command_lists_and_switches(cfg, sent):
    _case(id="case-1", title="Star Health · Gallstones")
    _case(id="case-2", title="Niva Bupa · Dengue")
    _post(_text("cases"))
    assert "Reply with a number" in _replies(sent)[0]

    _post(_text("2", mid="wamid.2"))
    assert store.load_session("whatsapp", SENDER)["case_id"] == "case-1"


def test_letter_command_sends_the_pdf(cfg, sent):
    case = _case(status=CaseStatus.READY)
    case.letter = Letter(subject="Appeal", english="Dear Sir,\n\nI appeal.", language="en")
    store.save_case(case)
    _post(_text("letter"))
    kind, _, filename, data, caption = sent[0]
    assert (kind, filename) == ("media", "kavach-appeal-letter.pdf")
    assert data[:4] == b"%PDF"
    assert "Check every detail" in caption


def test_letter_before_analysis_says_so(cfg, sent):
    _case(status=CaseStatus.COLLECTING)
    _post(_text("letter"))
    assert "reply *ANALYSE* first" in _replies(sent)[0]


# ── Documents ─────────────────────────────────────────────────────────────────────────


def _media_msg(kind: str = "image", mid: str = "wamid.9", caption: str | None = None) -> dict:
    media: dict = {"id": "media-1", "mime_type": "image/jpeg"}
    if caption:
        media["caption"] = caption
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": SENDER,
                                    "id": mid,
                                    "timestamp": "1760000000",
                                    "type": kind,
                                    kind: media,
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


def test_a_photo_starts_a_case_in_the_right_country(cfg, sent, monkeypatch):
    monkeypatch.setattr(
        wa, "download_media", lambda media_id: (b"\xff\xd8\xff\xe0jpeg", "image/jpeg", None)
    )
    _post(_media_msg(caption="My claim rejection"))

    cases = store.list_cases("dev-user")
    assert len(cases) == 1
    case = cases[0]
    assert case.country == "IN"  # +91
    assert case.title == "My claim rejection"
    assert [d.filename for d in case.documents] == ["whatsapp.jpg"]
    assert "1 document on this case" in _replies(sent)[0]


def test_a_pdf_keeps_its_filename_and_joins_the_existing_case(cfg, sent, monkeypatch):
    case = _case()
    case.documents.append(Document(id="d0", filename="letter.pdf", gcs_uri="/tmp/letter.pdf"))
    store.save_case(case)
    monkeypatch.setattr(
        wa, "download_media", lambda media_id: (b"%PDF-1.4 policy", "application/pdf", "policy.pdf")
    )
    _post(_media_msg(kind="document"))
    stored = store.load_case(case.id)
    assert [d.filename for d in stored.documents] == ["letter.pdf", "policy.pdf"]
    reply = _replies(sent)[0]
    assert "That's 2 documents" in reply
    assert "Reply *ANALYSE*" in reply
    assert "policy wording" not in reply  # the policy is what just arrived


def test_an_unsupported_format_is_refused(cfg, sent, monkeypatch):
    _case()
    monkeypatch.setattr(
        wa, "download_media", lambda media_id: (b"MZ", "application/x-msdownload", "x.exe")
    )
    _post(_media_msg(kind="document"))
    assert "I can read PDFs and photos" in _replies(sent)[0]
    assert store.load_case("case-1").documents == []


def test_a_voice_note_is_politely_declined(cfg, sent):
    _post(_media_msg(kind="audio"))
    assert "not voice notes or videos" in _replies(sent)[0]


def test_a_media_download_failure_tells_the_patient_to_retry(cfg, sent, monkeypatch):
    _case()

    def boom(media_id):
        raise wa.WhatsAppError("HTTP 500")

    monkeypatch.setattr(wa, "download_media", boom)
    _post(_media_msg())
    assert "couldn't download that file" in _replies(sent)[0]


# ── Analysis and redelivery ───────────────────────────────────────────────────────────


def test_analyse_runs_the_pipeline_and_reports_back(cfg, sent, monkeypatch):
    case = _case(status=CaseStatus.COLLECTING)
    case.documents.append(Document(id="d1", filename="letter.pdf", gcs_uri="/tmp/letter.pdf"))
    store.save_case(case)

    ran = []

    def fake_run(case_id: str) -> None:
        ran.append(case_id)
        done = store.load_case(case_id)
        done.status = CaseStatus.READY
        from kavach.models import Assessment

        done.assessment = Assessment(strength="strong", score=0.8)
        store.save_case(done)

    monkeypatch.setattr(channel, "run_case", fake_run)
    _post(_text("analyse"))

    assert ran == ["case-1"]
    assert "your case looks strong" in _replies(sent)[-1]


def test_analyse_without_documents_is_refused(cfg, sent, monkeypatch):
    _case()
    monkeypatch.setattr(channel, "run_case", lambda case_id: pytest.fail("must not run"))
    _post(_text("analyse"))
    assert "Send me the documents first" in _replies(sent)[0]


def test_analyse_is_capped_per_day(cfg, sent, monkeypatch):
    monkeypatch.setenv("ANALYSES_PER_DAY", "1")
    get_settings.cache_clear()
    case = _case()
    case.documents.append(Document(id="d1", filename="letter.pdf", gcs_uri="/tmp/letter.pdf"))
    store.save_case(case)

    def back_to_collecting(case_id: str) -> None:
        done = store.load_case(case_id)
        done.status = CaseStatus.COLLECTING
        store.save_case(done)

    monkeypatch.setattr(channel, "run_case", back_to_collecting)

    _post(_text("analyse"))
    _post(_text("analyse", mid="wamid.2"))  # the cap is checked before the run
    assert "up to 1 analyses a day" in _replies(sent)[-1]


def test_meta_redelivery_is_answered_once(cfg, sent):
    _post(_text("hi"))
    _post(_text("hi"))  # same message id, as Meta retries
    assert len(sent) == 1


# ── Reminders and the 24-hour window ──────────────────────────────────────────────────


def test_notice_is_free_form_inside_the_window(cfg, sent, monkeypatch):
    monkeypatch.setenv("WHATSAPP_TEMPLATE", "kavach_case_update")
    get_settings.cache_clear()
    monkeypatch.setattr(wa, "send_template", lambda to, params: pytest.fail("template not needed"))
    recent = datetime.now(UTC) - timedelta(hours=1)
    assert wa.send_notice(SENDER, "Deadline tomorrow", recent) == "text"
    assert "Deadline tomorrow" in _replies(sent)[0]


def test_notice_uses_the_template_outside_the_window(cfg, monkeypatch):
    monkeypatch.setenv("WHATSAPP_TEMPLATE", "kavach_case_update")
    get_settings.cache_clear()
    calls = []
    monkeypatch.setattr(wa, "send_template", lambda to, params: calls.append((to, params)))
    monkeypatch.setattr(wa, "send_text", lambda to, body: pytest.fail("window has closed"))
    old = datetime.now(UTC) - timedelta(hours=30)
    assert wa.send_notice(SENDER, "Deadline tomorrow", old) == "template"
    assert calls == [(SENDER, ["Deadline tomorrow"])]


def test_notice_is_skipped_rather_than_lost_silently(cfg, monkeypatch):
    old = datetime.now(UTC) - timedelta(days=7)
    assert wa.send_notice(SENDER, "Deadline tomorrow", old) == "skipped"


def test_a_naive_timestamp_from_firestore_still_opens_the_window(cfg, sent):
    naive = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
    assert wa.send_notice(SENDER, "Hello", naive) == "text"


def test_long_answers_are_split_on_word_boundaries(cfg):
    chunks = wa._chunks("word " * 2000)  # 10k characters
    assert len(chunks) > 1
    assert all(len(c) <= wa.TEXT_LIMIT for c in chunks)
    assert all(not c.startswith(" ") for c in chunks)


def test_tracker_tick_nudges_whatsapp_sessions(cfg, sent):
    case = _case(status=CaseStatus.FILED)
    case.next_deadline = datetime.now(UTC) - timedelta(days=1)  # the insurer is late
    store.save_case(case)
    store.save_session("whatsapp", SENDER, {"uid": "dev-user", "last_in_at": datetime.now(UTC)})

    resp = TestClient(app).post("/tracker/tick")
    assert resp.status_code == 200
    assert resp.json()["notified"] == 1
    assert "Bima Bharosa" in _replies(sent)[0]


def test_tracker_tick_skips_a_muted_session(cfg, sent):
    case = _case(status=CaseStatus.FILED)
    case.next_deadline = datetime.now(UTC) - timedelta(days=1)
    store.save_case(case)
    store.save_session(
        "whatsapp", SENDER, {"uid": "dev-user", "muted": True, "last_in_at": datetime.now(UTC)}
    )
    assert TestClient(app).post("/tracker/tick").json()["notified"] == 0
    assert sent == []


# ── Dry run ───────────────────────────────────────────────────────────────────────────


def test_dry_run_logs_instead_of_calling_meta(cfg):
    """No credentials and no network: sending must not raise, it must record."""
    assert wa.send_text(SENDER, "hello") == [{"dry_run": True}]


def test_sending_without_credentials_or_dry_run_is_an_error(cfg, monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("WHATSAPP_DRY_RUN", "false")
    get_settings.cache_clear()
    with pytest.raises(wa.WhatsAppError):
        wa.send_text(SENDER, "hello")


# ── The paywall applies on WhatsApp too ───────────────────────────────────────────────
#
# The app gates the PDFs in routers/filing.py, but this channel renders them itself, so it has
# to apply the same check — otherwise LETTER and FORM would hand out the paid pack for free.


def test_letter_and_form_are_withheld_until_the_appeal_pack_is_paid(cfg, sent, monkeypatch):
    monkeypatch.setenv("PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("APP_URL", "https://app.example")
    get_settings.cache_clear()

    case = _case(status=CaseStatus.READY)
    case.assessment = Assessment(strength="strong", score=0.8)
    case.letter = Letter(subject="Appeal", english="Dear Sir,", language="en")
    store.save_case(case)

    _post(_text("letter"))
    assert not any(kind == "media" for kind, *_ in sent)  # no PDF handed over
    reply = _replies(sent)[0]
    assert "isn't unlocked yet" in reply
    assert "Rs. 399" in reply  # the price, from the same PRICES table the app uses
    assert "https://app.example/case/case-1" in reply

    _post(_text("form", mid="wamid.2"))
    assert not any(kind == "media" for kind, *_ in sent)
    assert "isn't unlocked yet" in _replies(sent)[-1]


def test_the_pack_is_sent_once_the_case_is_paid(cfg, sent, monkeypatch):
    monkeypatch.setenv("PAYMENTS_ENABLED", "true")
    get_settings.cache_clear()

    case = _case(status=CaseStatus.READY)
    case.paid_at = datetime.now(UTC)
    case.letter = Letter(subject="Appeal", english="Dear Sir,", language="en")
    store.save_case(case)

    _post(_text("letter"))
    assert [s[2] for s in sent if s[0] == "media"] == ["kavach-appeal-letter.pdf"]


def test_free_mode_needs_no_payment(cfg, sent):
    """With payments off (the default) everything is downloadable, as before."""
    case = _case(status=CaseStatus.READY)
    case.letter = Letter(subject="Appeal", english="Dear Sir,", language="en")
    store.save_case(case)
    _post(_text("letter"))
    assert [s[2] for s in sent if s[0] == "media"] == ["kavach-appeal-letter.pdf"]


# ── Driving the tracker from a chat ───────────────────────────────────────────────────
#
# STATUS let a patient read the case; nothing let them advance it. FILED and REPLY are what turn
# a one-way notifier into something that can actually carry a dispute to the end.


def _assessed(**kwargs) -> Case:
    case = _case(**kwargs)
    case.assessment = Assessment(strength="strong", score=0.8)
    case.facts = CaseFacts(currency="INR", claim_amount=184000)
    store.save_case(case)
    return case


def test_help_mentions_the_tracker_commands(cfg, sent):
    _post(_text("help"))
    reply = _replies(sent)[0]
    assert "*FILED*" in reply and "*REPLY*" in reply and "*PREDISCHARGE*" in reply


def test_filed_starts_the_countdown(cfg, sent):
    _assessed(status=CaseStatus.READY)
    _post(_text("FILED"))

    case = store.load_case("case-1")
    assert case.status == CaseStatus.FILED
    assert case.next_deadline is not None
    reply = _replies(sent)[0]
    assert "filed with" in reply
    assert case.next_deadline.strftime("%d %b %Y") in reply


def test_filed_accepts_the_date_it_happened(cfg, sent):
    _assessed(status=CaseStatus.READY)
    _post(_text("FILED 2026-10-12"))

    # India's first rung is 15 days, so the deadline counts from the day they filed, not today.
    assert store.load_case("case-1").next_deadline.date() == date(2026, 10, 27)


def test_filed_refuses_a_date_it_cannot_read_or_one_in_the_future(cfg, sent):
    _assessed(status=CaseStatus.READY)
    _post(_text("FILED someday"))
    assert "couldn't read that date" in _replies(sent)[0]

    _post(_text("FILED 2099-01-01", mid="wamid.2"))
    assert "in the future" in _replies(sent)[-1]
    assert store.load_case("case-1").status == CaseStatus.READY  # untouched


def test_reply_paid_resolves_and_records_what_came_back(cfg, sent):
    _assessed(status=CaseStatus.FILED)
    _post(_text("REPLY PAID 112000"))

    case = store.load_case("case-1")
    assert case.status == CaseStatus.RESOLVED
    assert case.amount_recovered == 112000
    assert "Rs. 1,12,000 recovered" in _replies(sent)[0]


def test_reply_rejected_moves_to_the_next_step_and_names_the_one_that_refused(cfg, sent):
    _assessed(status=CaseStatus.FILED)
    _post(_text("REPLY REJECTED"))

    case = store.load_case("case-1")
    assert case.status == CaseStatus.ESCALATED
    assert case.escalation_step == 1
    reply = _replies(sent)[0]
    assert "Insurer grievance cell refused" in reply  # not the body it was just escalated to
    assert "Bima Bharosa" in reply


def test_reply_before_filing_is_redirected(cfg, sent):
    _assessed(status=CaseStatus.READY)
    _post(_text("REPLY PAID 5000"))
    assert "Reply *FILED*" in _replies(sent)[0]
    assert store.load_case("case-1").status == CaseStatus.READY


def test_reply_without_an_outcome_asks_for_one(cfg, sent):
    _assessed(status=CaseStatus.FILED)
    _post(_text("REPLY"))
    assert "*REPLY PAID 112000*" in _replies(sent)[0]


def test_predischarge_starts_a_different_kind_of_case(cfg, sent):
    _post(_text("PREDISCHARGE"))

    cases = store.list_cases("dev-user")
    assert len(cases) == 1
    assert cases[0].kind == "pre_discharge"
    assert cases[0].country == "IN"  # still from the dialling code
    assert store.load_session("whatsapp", SENDER)["case_id"] == cases[0].id
    assert "pre-discharge check" in _replies(sent)[0]


def test_analyse_on_a_predischarge_case_asks_for_the_right_documents(cfg, sent):
    _post(_text("PREDISCHARGE"))
    _post(_text("ANALYSE", mid="wamid.2"))
    assert "draft discharge summary first" in _replies(sent)[-1]


def test_the_patients_message_is_marked_read(cfg, sent, monkeypatch):
    seen = []
    monkeypatch.setattr(wa, "mark_read", lambda message_id: seen.append(message_id))
    _post(_text("hi", mid="wamid.read"))
    assert seen == ["wamid.read"]


def test_a_failed_read_receipt_still_answers_the_patient(cfg, sent, monkeypatch):
    def boom(message_id):
        raise wa.WhatsAppError("HTTP 500")

    monkeypatch.setattr(wa, "mark_read", boom)
    _post(_text("hi"))
    assert _replies(sent)  # the reply is not lost to a cosmetic failure


def test_meta_redelivery_is_not_marked_read_twice(cfg, sent, monkeypatch):
    seen = []
    monkeypatch.setattr(wa, "mark_read", lambda message_id: seen.append(message_id))
    _post(_text("hi", mid="wamid.dup"))
    _post(_text("hi", mid="wamid.dup"))
    assert seen == ["wamid.dup"]


# ── The parsers, on their own ─────────────────────────────────────────────────────────


def test_filed_date_parsing():
    today = date(2026, 10, 17)
    assert copy.filed_date("filed", today) == today
    assert copy.filed_date("FILED today", today) == today
    assert copy.filed_date("filed yesterday", today) == date(2026, 10, 16)
    assert copy.filed_date("sent 12/10/2026", today) == date(2026, 10, 12)
    assert copy.filed_date("filed 2026-10-12", today) == date(2026, 10, 12)
    assert copy.filed_date("filed whenever", today) is None


def test_reply_parsing():
    today = date(2026, 10, 17)
    assert copy.reply_request("reply paid 112000", today) == ("paid", 112000.0)
    assert copy.reply_request("reply partly 20,000", today) == ("partly_paid", 20000.0)
    assert copy.reply_request("reply rejected", today) == ("rejected", None)
    assert copy.reply_request("reply maybe", today) is None
