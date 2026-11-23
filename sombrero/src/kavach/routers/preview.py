"""Try before signing in: read one rejection letter and explain it, with nothing stored.

The public guides send visitors here. They see the decoded reason, how similar Ombudsman cases
ended and their deadline before being asked for a phone number. The file is read in memory
(a temp file for the model call, deleted at once), never saved, never logged, and the answer
leaves out names and policy or claim numbers. Rate-limited per visitor and per day because
the route is public.
"""

import hashlib
import logging
import tempfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from ..agents import code_decoder, intake
from ..config import get_settings
from ..models import DocType
from ..tools import packs, store
from .documents import ALLOWED

log = logging.getLogger(__name__)
router = APIRouter(prefix="/preview", tags=["preview"])

MAX_PREVIEW_BYTES = 10 * 1024 * 1024
MAX_TEXT = 12_000
COUNTRIES = {"IN", "SG", "MY"}


class PreviewStep(BaseModel):
    step: str
    dispute_body: str
    deadline_days: int


class PreviewGuide(BaseModel):
    slug: str
    total: int
    won_pct: int
    allowed: int
    partly_allowed: int
    dismissed: int


class PreviewResult(BaseModel):
    is_rejection: bool
    insurer: str | None = None
    diagnosis: str | None = None
    claim_amount: float | None = None
    amount_approved: float | None = None
    currency: str | None = None
    rejection_date: date | None = None
    rejection_category: str | None = None
    rejection_reason: str | None = None
    cited_clause: str | None = None
    decoded_code: str | None = None
    deadline: date | None = None  # last day to approach the final dispute body
    deadline_body: str | None = None
    ladder: list[PreviewStep] = []
    guide: PreviewGuide | None = None


def _visitor(request: Request) -> str:
    # Cloud Run puts the caller first in X-Forwarded-For. Only a hash is kept, for the quota.
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    ip = ip or (request.client.host if request.client else "unknown")
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def _check_quota(request: Request) -> None:
    s = get_settings()
    day = f"{datetime.now(UTC):%Y%m%d}"
    if not store.take_quota(f"preview-{_visitor(request)}-{day}", s.previews_per_ip_per_day):
        raise HTTPException(
            429,
            f"You can check up to {s.previews_per_ip_per_day} letters a day without signing in. "
            "Sign in to keep going.",
        )
    if not store.take_quota(f"preview-all-{day}", s.previews_per_day):
        raise HTTPException(429, "Too many people are checking letters right now. Please sign in.")


def explain(path: str, country: str) -> PreviewResult:
    result = intake.run([path])
    facts = result.facts
    is_letter = any(d.doc_type == DocType.REJECTION_LETTER for d in result.documents)
    if not is_letter and not facts.rejection_reason:
        return PreviewResult(is_rejection=False)
    decoded = code_decoder.decode(country, facts.tpa, facts.rejection_code)
    if decoded:
        facts.rejection_category = decoded["category"]
        facts.rejection_reason = facts.rejection_reason or decoded.get("meaning")
    pack = packs.load(country)
    limit = pack.get("limitation") or {}
    deadline = (
        facts.rejection_date + timedelta(days=limit["days"])
        if facts.rejection_date and limit.get("days")
        else None
    )
    category = facts.rejection_category.value if facts.rejection_category else None
    guide = None
    for g in (packs.guides(country) or {}).get("guides", []):
        if g["key"] == category:
            st = g["stats"]
            guide = PreviewGuide(
                slug=g["slug"], **{k: st[k] for k in PreviewGuide.model_fields if k != "slug"}
            )
    return PreviewResult(
        is_rejection=True,
        insurer=facts.insurer,
        diagnosis=facts.diagnosis,
        claim_amount=facts.claim_amount,
        amount_approved=facts.amount_approved,
        currency=facts.currency,
        rejection_date=facts.rejection_date,
        rejection_category=category,
        rejection_reason=facts.rejection_reason,
        cited_clause=facts.cited_clause,
        decoded_code=decoded.get("meaning") if decoded else None,
        deadline=deadline,
        deadline_body=limit.get("body"),
        ladder=[
            PreviewStep(
                step=s["step"], dispute_body=s["dispute_body"], deadline_days=s["deadline_days"]
            )
            for s in pack["dispute_process"]
        ],
        guide=guide,
    )


@router.post("", response_model=PreviewResult)
async def preview(
    request: Request,
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None, max_length=MAX_TEXT),
    country: str = Form(default="IN"),
) -> PreviewResult:
    """Explain a rejection letter without an account. Nothing is stored."""
    country = country.upper()
    if country not in COUNTRIES:
        raise HTTPException(400, "Kavach covers India, Singapore and Malaysia for now.")
    if file is None and not (text or "").strip():
        raise HTTPException(400, "Attach your rejection letter or paste its text.")
    if file is not None:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED:
            raise HTTPException(415, "Use a PDF, photo (JPG, PNG, WEBP) or text file.")
        data = await file.read(MAX_PREVIEW_BYTES + 1)
        if len(data) > MAX_PREVIEW_BYTES:
            raise HTTPException(413, "That file is over 10 MB. Try a photo of just the letter.")
        if not data:
            raise HTTPException(400, "That file is empty.")
    else:
        suffix, data = ".txt", text.strip().encode()
    _check_quota(request)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"letter{suffix}"
        path.write_bytes(data)
        try:
            return explain(str(path), country)
        except Exception as exc:  # noqa: BLE001 - any model/parse failure gets one friendly answer
            # The type only: the letter's content must never reach the logs.
            log.warning("preview: reading the letter failed: %s", type(exc).__name__)
            raise HTTPException(
                502, "We couldn't read that letter just now. Please try again."
            ) from None
