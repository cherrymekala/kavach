"""Email through Cloudflare Email Service: the appeal letter out, insurer replies back in.

Out: the REST send API with the patient in CC and Reply-To set to MAIL_REPLY_TO. Cloudflare
returns the message's id, which is saved against the case (store.save_mail_thread).

In: Cloudflare Email Routing hands mail for MAIL_REPLY_TO to the Worker in pinwheel/, which
posts it to /mail/inbound with MAIL_INBOUND_TOKEN. Mail clients put the id of the message
being answered in In-Reply-To/References, so the reply finds its case without per-case
addresses (Email Routing has no catch-all on subdomains, and the apex mail is Google
Workspace). With no API token everything runs dry (logged, not sent).
"""

import base64
import hmac
import logging
import re
import uuid

import httpx

from ..config import get_settings

log = logging.getLogger(__name__)

API = "https://api.cloudflare.com/client/v4/accounts/{account}/email/sending/send"
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MESSAGE_ID = re.compile(r"<[^<>\s]+>")
_NAMED = re.compile(r"^\s*(.*?)\s*<([^<>\s]+)>\s*$")

# Cloud Run can't deploy with an empty secret, so the secret holds this until the real token is
# added (gcloud secrets versions add cloudflare-email-token …): until then, sends are dry runs.
PLACEHOLDER = "unset"


class MailError(Exception):
    """Sending failed; the message is safe to show the patient."""


def _token() -> str:
    token = get_settings().cloudflare_email_token.strip()
    return "" if token == PLACEHOLDER else token


def configured() -> bool:
    s = get_settings()
    return bool(_token() and s.cloudflare_account_id and s.mail_from)


def reply_address() -> str | None:
    return get_settings().mail_reply_to or None


def token_ok(token: str | None) -> bool:
    secret = get_settings().mail_inbound_token
    return bool(secret) and hmac.compare_digest((token or "").encode(), secret.encode())


def message_ids(*headers: str | None) -> list[str]:
    """Every <message-id> in In-Reply-To / References headers, newest last."""
    return [m for h in headers if h for m in _MESSAGE_ID.findall(h)]


def _sender(value: str) -> dict | str:
    """ "Kavach Appeals <appeals@x>" → {"address", "name"}; a bare address stays a string."""
    m = _NAMED.match(value)
    if m and m.group(1):
        return {"address": m.group(2), "name": m.group(1).strip('"')}
    return value.strip()


def send(
    to: str,
    subject: str,
    text: str,
    *,
    cc: str | None = None,
    reply_to: str | None = None,
    attachments: list[tuple[str, bytes, str]] = (),
) -> str:
    """Send one email; returns its Message-ID (a <dry-run-…> id without an API token)."""
    s = get_settings()
    payload: dict = {
        "from": _sender(s.mail_from or "Kavach <appeals@example.invalid>"),
        "to": [to],
        "subject": subject,
        "text": text,
    }
    if cc:
        payload["cc"] = [cc]
    if reply_to:
        payload["reply_to"] = reply_to
    if attachments:
        payload["attachments"] = [
            {
                "content": base64.b64encode(data).decode(),
                "filename": name,
                "type": mime,
                "disposition": "attachment",
            }
            for name, data, mime in attachments
        ]
    if not _token():
        log.info("mail: dry run, not sent: %s", subject)
        # A unique id still threads local replies to the case (see store.save_mail_thread).
        return f"<dry-run-{uuid.uuid4().hex}@kavach.local>"
    try:
        r = httpx.post(
            API.format(account=s.cloudflare_account_id),
            json=payload,
            headers={"Authorization": f"Bearer {_token()}"},
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise MailError("We couldn't reach the email service. Please try again.") from exc
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code != 200 or not body.get("success"):
        errors = body.get("errors") or []
        reason = errors[0].get("message", "") if errors else ""
        log.error("mail: Cloudflare refused (%s): %s", r.status_code, errors)
        raise MailError(
            "The email was not sent. Please try again in a few minutes."
            + (f" ({reason})" if reason else "")
        )
    result = body.get("result") or {}
    if result.get("permanent_bounces"):
        raise MailError("The insurer's address bounced. Check the email address and try again.")
    return result.get("message_id", "")
