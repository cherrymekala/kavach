from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from ..auth import current_user
from ..config import get_settings
from ..models import Case, CaseEvent
from ..tools import payments, store

router = APIRouter(tags=["payments"])


class RazorpayPaid(BaseModel):
    order_id: str
    payment_id: str
    signature: str


def _own(case_id: str, uid: str) -> Case:
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    return case


def _mark_paid(case: Case, ref: str) -> None:
    if case.paid_at:
        return  # Stripe retries webhooks; the browser may also report the same payment
    currency, amount = payments.price(case.country) or ("", 0)
    case.paid_at, case.payment_ref = datetime.now(UTC), ref
    case.events.append(
        CaseEvent(
            at=case.paid_at,
            kind="payment",
            text=f"Appeal pack unlocked ({currency} {amount / 100:,.0f}).",
        )
    )
    store.save_case(case)


@router.post("/cases/{case_id}/checkout")
def checkout(case_id: str, uid: str = Depends(current_user)) -> dict:
    """Start paying for the appeal pack. India: a Razorpay order for the in-page checkout.
    Singapore/Malaysia: a Stripe Checkout URL to redirect to."""
    if not get_settings().payments_enabled:
        raise HTTPException(400, "Payments are switched off; the appeal pack is free.")
    case = _own(case_id, uid)
    if not case.assessment:
        raise HTTPException(409, "Run the analysis first.")
    if case.paid_at:
        raise HTTPException(409, "The appeal pack is already unlocked.")
    if not payments.price(case.country):
        raise HTTPException(400, f"No price set for {case.country}.")
    try:
        if payments.provider(case.country) == "razorpay":
            return payments.razorpay_order(case)
        return payments.stripe_checkout(case)
    except payments.PaymentError as exc:
        raise HTTPException(502, "The payment service didn't respond. Please try again.") from exc


@router.post("/cases/{case_id}/payment/razorpay", response_model=Case)
def razorpay_paid(case_id: str, body: RazorpayPaid, uid: str = Depends(current_user)) -> Case:
    """Razorpay Checkout's success handler posts here; we check the signature ourselves."""
    case = _own(case_id, uid)
    if not payments.razorpay_signature_ok(body.order_id, body.payment_id, body.signature):
        raise HTTPException(400, "We couldn't verify that payment.")
    if payments.razorpay_order_case(body.order_id) != case.id:
        raise HTTPException(400, "That payment was for a different case.")
    _mark_paid(case, body.payment_id)
    return case


@router.post("/payments/stripe/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header("")) -> dict:
    try:
        event = payments.stripe_event(await request.body(), stripe_signature)
    except payments.PaymentError as exc:
        raise HTTPException(400, str(exc)) from exc
    session = event.get("data", {}).get("object", {})
    if (
        event.get("type") == "checkout.session.completed"
        and session.get("payment_status") == "paid"
    ):
        case = store.load_case((session.get("metadata") or {}).get("case_id", ""))
        if case:
            _mark_paid(case, session.get("id", ""))
    return {"received": True}
