"""Appeal-pack payments: Razorpay for India, Stripe Checkout for Singapore and Malaysia.

Plain HTTPS calls (no SDKs). A case is marked paid only after a server-side signature check:
Razorpay's payment signature (HMAC-SHA256 of order|payment with the key secret) or Stripe's
signed `checkout.session.completed` webhook. The browser can't mark a case paid by itself.
"""

import hashlib
import hmac
import json
import time

import httpx

from ..config import get_settings
from ..models import Case

# Smallest currency unit (paise / cents / sen). Within the ₹299–499 / S$29–49 pitch range.
PRICES = {"IN": ("INR", 39900), "SG": ("SGD", 3900), "MY": ("MYR", 9900)}
PRODUCT = "Kavach appeal pack"
STRIPE_TOLERANCE = 300  # seconds between Stripe signing a webhook and us receiving it


class PaymentError(Exception):
    pass


def price(country: str) -> tuple[str, int] | None:
    return PRICES.get(country.upper())


def provider(country: str) -> str:
    return "razorpay" if country.upper() == "IN" else "stripe"


def is_unlocked(case: Case) -> bool:
    return not get_settings().payments_enabled or case.paid_at is not None


# ── Razorpay ──────────────────────────────────────────────────────────────────────────


def razorpay_order(case: Case) -> dict:
    s = get_settings()
    currency, amount = PRICES["IN"]
    try:
        r = httpx.post(
            "https://api.razorpay.com/v1/orders",
            auth=(s.razorpay_key_id, s.razorpay_key_secret),
            json={
                "amount": amount,
                "currency": currency,
                "receipt": case.id[:40],
                "notes": {"case_id": case.id},
            },
            timeout=20,
        )
    except httpx.HTTPError as exc:  # timeout, DNS, connection reset: retryable, not a 500
        raise PaymentError(f"Razorpay unreachable: {exc}") from exc
    if r.status_code >= 400:
        raise PaymentError(f"Razorpay: {r.text[:200]}")
    order = r.json()
    return {
        "provider": "razorpay",
        "key_id": s.razorpay_key_id,
        "order_id": order["id"],
        "amount": amount,
        "currency": currency,
        "name": PRODUCT,
    }


def razorpay_signature_ok(order_id: str, payment_id: str, signature: str) -> bool:
    secret = get_settings().razorpay_key_secret
    if not secret:
        # HMAC-SHA256 with an empty key is computable by anyone, so an unconfigured key secret
        # would turn this check into a rubber stamp. Refuse instead of trusting the caller.
        return False
    expected = hmac.new(
        secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def razorpay_order_case(order_id: str) -> str | None:
    """The case an order was created for (from its notes), so a payment can't unlock another.

    Returns None when Razorpay has no such order. Raises PaymentError when Razorpay itself is
    unreachable, so the caller can say "please try again" rather than accuse a patient who has
    just paid of using someone else's payment.
    """
    s = get_settings()
    try:
        r = httpx.get(
            f"https://api.razorpay.com/v1/orders/{order_id}",
            auth=(s.razorpay_key_id, s.razorpay_key_secret),
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise PaymentError(f"Razorpay unreachable: {exc}") from exc
    if r.status_code == 404:
        return None  # no such order
    if r.status_code >= 400:
        raise PaymentError(f"Razorpay order lookup: {r.status_code} {r.text[:200]}")
    return (r.json().get("notes") or {}).get("case_id")


# ── Stripe ────────────────────────────────────────────────────────────────────────────


def stripe_checkout(case: Case) -> dict:
    s = get_settings()
    currency, amount = PRICES[case.country.upper()]
    back = f"{s.app_url.rstrip('/')}/case/{case.id}"
    try:
        r = httpx.post(
            "https://api.stripe.com/v1/checkout/sessions",
            auth=(s.stripe_secret_key, ""),
            data={
                "mode": "payment",
                "client_reference_id": case.id,
                "metadata[case_id]": case.id,
                "line_items[0][quantity]": "1",
                "line_items[0][price_data][currency]": currency.lower(),
                "line_items[0][price_data][unit_amount]": str(amount),
                "line_items[0][price_data][product_data][name]": PRODUCT,
                "success_url": f"{back}?paid=1",
                "cancel_url": back,
            },
            timeout=20,
        )
    except httpx.HTTPError as exc:  # retryable, so surface it as a 502 rather than a 500
        raise PaymentError(f"Stripe unreachable: {exc}") from exc
    if r.status_code >= 400:
        raise PaymentError(f"Stripe: {r.text[:200]}")
    return {"provider": "stripe", "url": r.json()["url"], "amount": amount, "currency": currency}


def stripe_event(payload: bytes, header: str, now: float | None = None) -> dict:
    """Verify a Stripe webhook (`Stripe-Signature: t=...,v1=...`) and return the event."""
    secret = get_settings().stripe_webhook_secret
    if not secret:
        # Without a secret the HMAC key is empty and therefore public: anyone can sign a
        # checkout.session.completed for any case_id and unlock the appeal pack for free.
        # This endpoint unlocks cases, so an unconfigured secret must refuse, never pass.
        raise PaymentError("Stripe webhooks are not configured.")
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    signatures = [
        v for k, v in (p.split("=", 1) for p in header.split(",") if "=" in p) if k == "v1"
    ]
    try:
        ts = int(parts.get("t", ""))
    except ValueError as exc:
        raise PaymentError("Bad Stripe signature header.") from exc
    if abs((now or time.time()) - ts) > STRIPE_TOLERANCE:
        raise PaymentError("Stripe webhook too old.")
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    if not signatures or not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise PaymentError("Bad Stripe signature.")
    return json.loads(payload)
