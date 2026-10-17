import hashlib
import hmac
import json
import time

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
