"""Email through Postmark: the appeal letter out to the insurer, their replies back in.

Each case gets its own Reply-To address, `case-<id>-<sig>@<inbound domain>`, signed with
MAIL_INBOUND_TOKEN so a reply can only ever land in the case it was meant for. Postmark's
inbound webhook posts replies to /mail/inbound?token=<MAIL_INBOUND_TOKEN>. With no server
token everything runs dry (logged, not sent), like the WhatsApp channel in local dev.
"""

import base64
import hashlib
import hmac
import logging
import re

import httpx

from ..config import get_settings

log = logging.getLogger(__name__)

API = "https://api.postmarkapp.com/email"
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_REPLY = re.compile(r"case-([0-9a-f]{32})-([0-9a-f]{10})@", re.IGNORECASE)


# Cloud Run can't deploy with an empty secret, so the secret holds this until the real token is
# added (gcloud secrets versions add postmark-server-token …): until then, sends are dry runs.
PLACEHOLDER = "unset"


def _token() -> str:
    token = get_settings().postmark_server_token.strip()
    return "" if token == PLACEHOLDER else token


class MailError(Exception):
    """Sending failed; the message is safe to show the patient."""


def configured() -> bool:
    return bool(_token() and get_settings().mail_from)


def _sig(case_id: str) -> str:
    key = get_settings().mail_inbound_token.encode()
    return hmac.new(key, case_id.encode(), hashlib.sha256).hexdigest()[:10]


def reply_address(case_id: str) -> str | None:
    s = get_settings()
    if not (s.mail_inbound_domain and s.mail_inbound_token):
        return None
    return f"case-{case_id}-{_sig(case_id)}@{s.mail_inbound_domain}"


def case_for_addresses(addresses: list[str]) -> str | None:
    """The case a reply was sent to, if any recipient is a correctly signed case address."""
    if not get_settings().mail_inbound_token:
        return None
    for address in addresses:
        m = _REPLY.search(address or "")
        if m and hmac.compare_digest(m.group(2).lower(), _sig(m.group(1).lower())):
            return m.group(1).lower()
    return None


def token_ok(token: str | None) -> bool:
    secret = get_settings().mail_inbound_token
    return bool(secret) and hmac.compare_digest((token or "").encode(), secret.encode())


def send(
    to: str,
    subject: str,
    text: str,
    *,
    cc: str | None = None,
    reply_to: str | None = None,
    attachments: list[tuple[str, bytes, str]] = (),
) -> str:
    """Send one email; returns Postmark's MessageID ("dry-run" without a server token)."""
    s = get_settings()
    payload = {
        "From": s.mail_from or "Kavach <appeals@example.invalid>",
        "To": to,
        "Subject": subject,
        "TextBody": text,
        "MessageStream": "outbound",
    }
    if cc:
        payload["Cc"] = cc
    if reply_to:
        payload["ReplyTo"] = reply_to
    if attachments:
        payload["Attachments"] = [
            {"Name": name, "Content": base64.b64encode(data).decode(), "ContentType": mime}
            for name, data, mime in attachments
        ]
    if not _token():
        log.info("mail: dry run, not sent: %s", subject)
        return "dry-run"
    try:
        r = httpx.post(
            API,
            json=payload,
            headers={
                "X-Postmark-Server-Token": _token(),
                "Accept": "application/json",
            },
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise MailError("We couldn't reach the email service. Please try again.") from exc
    if r.status_code != 200:
        try:
            reason = r.json().get("Message", "")
        except ValueError:
            reason = ""
        log.error("mail: Postmark refused (%s): %s", r.status_code, reason)
        raise MailError(
            f"The email was not sent{': ' + reason if reason else ''}. Please try again."
        )
    return r.json().get("MessageID", "")
