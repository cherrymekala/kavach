import hashlib
import hmac
import json
import time
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from kavach.config import get_settings
from kavach.main import app
from kavach.models import Assessment, Case, Letter
from kavach.tools import payments, store

RZP_SECRET = "rzp_secret"
STRIPE_SECRET = "whsec_test"


def _case(case_id: str = "p1", country: str = "IN") -> Case:
    case = Case(
        id=case_id,
        owner="dev-user",
        country=country,
        assessment=Assessment(strength="strong", score=0.8),
        letter=Letter(subject="Appeal", english="Dear Sir"),
    )
    store.save_case(case)
    return case


@pytest.fixture
def paid_mode(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_key")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", RZP_SECRET)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", STRIPE_SECRET)
    get_settings.cache_clear()
    store._memory.clear()
    yield TestClient(app)
    get_settings.cache_clear()


def test_everything_is_free_when_payments_are_off(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.delenv("PAYMENTS_ENABLED", raising=False)
    get_settings.cache_clear()
    _case()
    client = TestClient(app)
    assert client.get("/cases/p1/letter.pdf").status_code == 200
    assert client.get("/packs/IN").json()["price_amount"] is None
    get_settings.cache_clear()


def test_pack_downloads_need_payment_and_the_price_is_public(paid_mode):
    _case()
    assert paid_mode.get("/cases/p1/letter.pdf").status_code == 402
    assert paid_mode.get("/cases/p1/filing.pdf").status_code == 402
    info = paid_mode.get("/packs/IN").json()
    assert (info["price_amount"], info["price_currency"], info["payment_provider"]) == (
        39900,
        "INR",
        "razorpay",
    )
    assert paid_mode.get("/packs/SG").json()["payment_provider"] == "stripe"


def test_razorpay_checkout_creates_an_order_for_the_case(paid_mode, monkeypatch):
    _case()
    sent = {}

    class _Resp:
        status_code = 200

        def json(self):
            return {"id": "order_1"}

    def fake_post(url, **kw):
        sent.update(url=url, **kw)
        return _Resp()

    monkeypatch.setattr(payments.httpx, "post", fake_post)
    r = paid_mode.post("/cases/p1/checkout").json()
    assert r == {
        "provider": "razorpay",
        "key_id": "rzp_test_key",
        "order_id": "order_1",
        "amount": 39900,
        "currency": "INR",
        "name": payments.PRODUCT,
    }
    assert sent["json"]["notes"] == {"case_id": "p1"}


def _rzp_sig(order: str, payment: str) -> str:
    return hmac.new(RZP_SECRET.encode(), f"{order}|{payment}".encode(), hashlib.sha256).hexdigest()


def test_razorpay_payment_unlocks_only_with_a_valid_signature_for_this_case(paid_mode, monkeypatch):
    _case()
    _case("other")
    monkeypatch.setattr(
        payments, "razorpay_order_case", lambda order: {"order_1": "p1"}.get(order, "other")
    )
    bad = {"order_id": "order_1", "payment_id": "pay_1", "signature": "forged"}
    assert paid_mode.post("/cases/p1/payment/razorpay", json=bad).status_code == 400

    # A real payment for another case's order can't unlock this one.
    elsewhere = {
        "order_id": "order_2",
        "payment_id": "pay_2",
        "signature": _rzp_sig("order_2", "pay_2"),
    }
    assert paid_mode.post("/cases/p1/payment/razorpay", json=elsewhere).status_code == 400

    good = {"order_id": "order_1", "payment_id": "pay_1", "signature": _rzp_sig("order_1", "pay_1")}
    case = paid_mode.post("/cases/p1/payment/razorpay", json=good).json()
    assert case["paid_at"] and case["payment_ref"] == "pay_1"
    assert case["events"][-1]["kind"] == "payment"
    assert paid_mode.get("/cases/p1/letter.pdf").status_code == 200


def _stripe_post(client, event: dict, ts: int | None = None, secret: str = STRIPE_SECRET):
    body = json.dumps(event).encode()
    ts = ts or int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return client.post(
        "/payments/stripe/webhook",
        content=body,
        headers={"Stripe-Signature": f"t={ts},v1={sig}", "Content-Type": "application/json"},
    )


def test_stripe_webhook_unlocks_once_and_rejects_forgeries(paid_mode):
    _case("s1", "SG")
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_1", "payment_status": "paid", "metadata": {"case_id": "s1"}}},
    }
    assert _stripe_post(paid_mode, event, secret="wrong").status_code == 400
    assert _stripe_post(paid_mode, event, ts=int(time.time()) - 3600).status_code == 400
    assert store.load_case("s1").paid_at is None

    assert _stripe_post(paid_mode, event).status_code == 200
    assert _stripe_post(paid_mode, event).status_code == 200  # Stripe retries
    case = store.load_case("s1")
    assert case.payment_ref == "cs_1" and [e.kind for e in case.events].count("payment") == 1


# ── Regression: an unconfigured secret must never become a rubber stamp ───────────────
#
# HMAC-SHA256 with an empty key is computable by anyone, so if payments are switched on while
# the signing secret is missing (a Secret Manager entry with no version, a renamed secret, a
# half-finished local .env) the "verify" step would accept anything. These tests pin the refusal.


def _payments_without(monkeypatch, **missing: str) -> None:
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_key")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", RZP_SECRET)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", STRIPE_SECRET)
    for key, value in missing.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    store._memory.clear()


def test_stripe_webhook_cannot_unlock_a_case_when_no_secret_is_configured(monkeypatch):
    _payments_without(monkeypatch, STRIPE_WEBHOOK_SECRET="")
    try:
        _case("s2", "SG")
        client = TestClient(app)
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {"id": "cs_x", "payment_status": "paid", "metadata": {"case_id": "s2"}}
            },
        }
        body = json.dumps(event).encode()
        ts = int(time.time())
        # Exactly what an attacker with no Stripe account can compute when the key is empty.
        forged = hmac.new(b"", f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
        r = client.post(
            "/payments/stripe/webhook",
            content=body,
            headers={"Stripe-Signature": f"t={ts},v1={forged}"},
        )
        assert r.status_code == 400
        assert store.load_case("s2").paid_at is None
        assert client.get("/cases/s2/letter.pdf").status_code == 402
    finally:
        get_settings.cache_clear()


def test_razorpay_cannot_unlock_a_case_when_no_key_secret_is_configured(monkeypatch):
    _payments_without(monkeypatch, RAZORPAY_KEY_SECRET="")
    try:
        _case()
        forged = hmac.new(b"", b"order_1|pay_1", hashlib.sha256).hexdigest()
        r = TestClient(app).post(
            "/cases/p1/payment/razorpay",
            json={"order_id": "order_1", "payment_id": "pay_1", "signature": forged},
        )
        assert r.status_code == 400
        assert store.load_case("p1").paid_at is None
    finally:
        get_settings.cache_clear()


def test_razorpay_outage_does_not_accuse_a_patient_who_has_paid(paid_mode, monkeypatch):
    """A failed order lookup is retryable; "that payment was for a different case" is not."""

    def unreachable(order_id: str):
        raise payments.PaymentError("Razorpay unreachable: timed out")

    monkeypatch.setattr(payments, "razorpay_order_case", unreachable)
    _case()
    body = {"order_id": "order_1", "payment_id": "pay_1", "signature": _rzp_sig("order_1", "pay_1")}
    r = paid_mode.post("/cases/p1/payment/razorpay", json=body)
    assert r.status_code == 502
    assert store.load_case("p1").paid_at is None


# ── Checkout guards and the Stripe creation path ──────────────────────────────────────
#
# The original suite covered the two "payment succeeded" paths. Everything a patient can hit
# *before* paying was untested, and so was the Stripe request we build.


def test_checkout_is_refused_when_payments_are_off(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.delenv("PAYMENTS_ENABLED", raising=False)
    get_settings.cache_clear()
    try:
        _case()
        r = TestClient(app).post("/cases/p1/checkout")
        assert r.status_code == 400
        assert "switched off" in r.json()["detail"]
    finally:
        get_settings.cache_clear()


def test_checkout_needs_an_assessment_first(paid_mode):
    store.save_case(Case(id="bare", owner="dev-user", country="IN"))
    r = paid_mode.post("/cases/bare/checkout")
    assert r.status_code == 409
    assert "analysis" in r.json()["detail"].lower()


def test_checkout_refuses_a_case_that_is_already_paid(paid_mode):
    case = _case()
    case.paid_at = datetime.now(UTC)
    store.save_case(case)
    r = paid_mode.post("/cases/p1/checkout")
    assert r.status_code == 409
    assert "already unlocked" in r.json()["detail"]


def test_checkout_refuses_a_country_with_no_price(paid_mode):
    store.save_case(
        Case(
            id="usd",
            owner="dev-user",
            country="US",
            assessment=Assessment(strength="strong", score=0.8),
        )
    )
    r = paid_mode.post("/cases/usd/checkout")
    assert r.status_code == 400
    assert "No price" in r.json()["detail"]


def test_checkout_reports_a_provider_outage_as_retryable(paid_mode, monkeypatch):
    def boom(case):
        raise payments.PaymentError("Razorpay unreachable: timed out")

    monkeypatch.setattr(payments, "razorpay_order", boom)
    _case()
    r = paid_mode.post("/cases/p1/checkout")
    assert r.status_code == 502  # not a 500, and the copy tells them to try again
    assert "try again" in r.json()["detail"]


def test_stripe_checkout_builds_a_session_for_the_case(paid_mode, monkeypatch):
    store.save_case(
        Case(
            id="s3",
            owner="dev-user",
            country="SG",
            assessment=Assessment(strength="strong", score=0.8),
        )
    )
    sent = {}

    class _Resp:
        status_code = 200

        def json(self):
            return {"url": "https://checkout.stripe.com/c/pay/cs_test_1"}

    def fake_post(url, **kw):
        sent.update(url=url, **kw)
        return _Resp()

    monkeypatch.setattr(payments.httpx, "post", fake_post)
    r = paid_mode.post("/cases/s3/checkout").json()
    assert r == {
        "provider": "stripe",
        "url": "https://checkout.stripe.com/c/pay/cs_test_1",
        "amount": 3900,
        "currency": "SGD",
    }
    form = sent["data"]
    assert form["metadata[case_id]"] == "s3"
    assert form["client_reference_id"] == "s3"
    assert form["line_items[0][price_data][currency]"] == "sgd"  # Stripe wants lower case
    assert form["line_items[0][price_data][unit_amount]"] == "3900"
    assert form["success_url"].endswith("/case/s3?paid=1")


# ── The hearing is part of the pack too ───────────────────────────────────────────────


def test_hearing_is_locked_until_the_pack_is_paid(paid_mode):
    _case()
    with paid_mode.websocket_connect("/cases/p1/hearing") as ws:
        ws.send_json({"token": None})  # AUTH_DISABLED, so the token is not the blocker
        payload = ws.receive_json()
    assert "Unlock the appeal pack" in payload["error"]


def test_authorising_a_hearing_passes_once_paid(paid_mode):
    from kavach.routers import hearing as hearing_router

    case = _case()
    case.paid_at = datetime.now(UTC)
    store.save_case(case)
    assert hearing_router._authorise({"token": None}, "p1").id == "p1"


def test_the_phone_menu_hides_the_rehearsal_until_paid(paid_mode):
    from kavach.routers import voice as voice_router

    case = _case()
    assert "Press 2" not in voice_router._menu(case)  # locked, so it is not even offered
    case.paid_at = datetime.now(UTC)
    store.save_case(case)
    assert "Press 2" in voice_router._menu(case)
