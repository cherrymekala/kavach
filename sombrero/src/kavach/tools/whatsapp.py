"""WhatsApp Cloud API (Meta) — sending, receiving and verifying.

Outbound calls go to `POST /{version}/{phone-number-id}/messages` with a Bearer access token.
Inbound webhooks are signed by Meta with HMAC-SHA256 over the *raw* body, in the
`X-Hub-Signature-256` header — verify against the bytes you received, not a re-serialised dict.

Two rules from Meta shape the design:

* **Free-form messages only inside a 24-hour window.** After the patient's last message we can
  send anything; after that, only a pre-approved template. `send_notice` picks the right one, so
  a deadline reminder still goes out a week later.
* **Webhooks must be acknowledged fast.** Otherwise Meta retries and the patient gets duplicate
  replies; the router therefore returns 200 immediately and does the work in the background.

With no credentials and `AUTH_DISABLED`/`WHATSAPP_DRY_RUN`, outbound calls are logged instead of
sent, which is how local dev and the smoke script exercise the whole flow.
"""

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime, timedelta

import httpx

from ..config import get_settings

log = logging.getLogger("kavach.whatsapp")

GRAPH = "https://graph.facebook.com"
WINDOW = timedelta(hours=24)  # Meta's free-form messaging window
TEXT_LIMIT = 4096  # WhatsApp's maximum body length
MEDIA_LIMIT = 20 * 1024 * 1024  # same ceiling as the web uploader


class WhatsAppError(RuntimeError):
    """Meta refused the call. The message is safe to log, never to show a patient."""


# ── Inbound: does this really come from Meta? ─────────────────────────────────────────


def signature_ok(body: bytes, header: str | None) -> bool:
    """Check Meta's X-Hub-Signature-256 over the raw request body."""
    s = get_settings()
    if not s.whatsapp_app_secret:
        # Local dev without a Meta app: only tolerate this when auth is already off.
        return s.auth_disabled
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(s.whatsapp_app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def challenge(params: dict) -> str | None:
    """Answer Meta's GET subscription check, or None when the token is wrong."""
    s = get_settings()
    if params.get("hub.mode") != "subscribe":
        return None
    if not hmac.compare_digest(params.get("hub.verify_token", ""), s.whatsapp_verify_token):
        return None
    return params.get("hub.challenge", "")


# ── The Graph API ─────────────────────────────────────────────────────────────────────


def configured() -> bool:
    s = get_settings()
    return bool(s.whatsapp_phone_number_id and s.whatsapp_access_token)


def _dry() -> bool:
    return not configured() and (get_settings().auth_disabled or get_settings().whatsapp_dry_run)


def _error(resp: httpx.Response) -> str:
    try:
        return resp.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):  # non-JSON body, e.g. an HTML gateway page
        return f"HTTP {resp.status_code}"


def _call(path: str, payload: dict | None = None, method: str = "POST") -> dict:
    """One Graph API call, or a logged no-op in dry-run mode."""
    s = get_settings()
    if _dry():
        log.warning(
            "whatsapp dry run %s %s: %s", method, path, json.dumps(payload, default=str)[:2000]
        )
        return {"dry_run": True}
    if not configured():
        raise WhatsAppError(
            "WhatsApp is not configured: set WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN."
        )
    url = f"{GRAPH}/{s.whatsapp_api_version}/{path}"
    headers = {"Authorization": f"Bearer {s.whatsapp_access_token}"}
    with httpx.Client(timeout=30) as client:
        resp = client.request(method, url, headers=headers, json=payload)
    if resp.status_code >= 400:
        raise WhatsAppError(f"{method} {path}: {_error(resp)}")
    return resp.json()


def _chunks(text: str, limit: int = TEXT_LIMIT) -> list[str]:
    """Split on paragraph, then line, then word boundaries so nothing is cut mid-word."""
    text = text.strip()
    if len(text) <= limit:
        return [text] if text else []
    parts, current = [], ""
    for block in text.split("\n"):
        candidate = f"{current}\n{block}" if current else block
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            parts.append(current)
        while len(block) > limit:
            cut = block.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            parts.append(block[:cut])
            block = block[cut:].lstrip()
        current = block
    if current:
        parts.append(current)
    return parts


def mark_read(message_id: str) -> dict:
    """Blueprint the patient's message as read, so they see the ticks and know we have it."""
    s = get_settings()
    return _call(
        f"{s.whatsapp_phone_number_id}/messages",
        {"messaging_product": "whatsapp", "status": "read", "message_id": message_id},
    )


def send_text(to: str, body: str) -> list[dict]:
    """Send a reply, splitting anything over WhatsApp's 4096-character limit."""
    s = get_settings()
    sent = []
    for chunk in _chunks(body):
        sent.append(
            _call(
                f"{s.whatsapp_phone_number_id}/messages",
                {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to,
                    "type": "text",
                    "text": {"preview_url": False, "body": chunk},
                },
            )
        )
    return sent


def _upload(data: bytes, filename: str, mime: str) -> str:
    """Upload media once, then reference it by id (Meta deletes it after 30 days)."""
    s = get_settings()
    if _dry():
        log.warning("whatsapp dry run upload: %s (%s, %d bytes)", filename, mime, len(data))
        return "dry-run-media-id"
    if not configured():
        raise WhatsAppError("WhatsApp is not configured: cannot upload media.")
    url = f"{GRAPH}/{s.whatsapp_api_version}/{s.whatsapp_phone_number_id}/media"
    headers = {"Authorization": f"Bearer {s.whatsapp_access_token}"}
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            url,
            headers=headers,
            data={"messaging_product": "whatsapp", "type": mime},
            files={"file": (filename, data, mime)},
        )
    if resp.status_code >= 400:
        raise WhatsAppError(f"media upload: {_error(resp)}")
    return resp.json()["id"]


def send_media(to: str, data: bytes, filename: str, mime: str, caption: str | None = None) -> dict:
    """Send a PDF or image as a document/image message."""
    s = get_settings()
    media_id = _upload(data, filename, mime)
    kind = "image" if mime.startswith("image/") else "document"
    media: dict = {"id": media_id}
    if kind == "document":
        media["filename"] = filename
    if caption:
        media["caption"] = caption[:1024]
    return _call(
        f"{s.whatsapp_phone_number_id}/messages",
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": kind,
            kind: media,
        },
    )


def download_media(media_id: str) -> tuple[bytes, str, str | None]:
    """Fetch inbound media: metadata first (so we can refuse oversized files), then bytes.

    Returns (data, mime_type, filename). Images carry no filename, so it stays None.
    """
    if _dry():
        raise WhatsAppError("WhatsApp is in dry-run mode: inbound media cannot be downloaded.")
    meta = _call(media_id, method="GET")
    size = int(meta.get("file_size") or 0)
    if size > MEDIA_LIMIT:
        raise WhatsAppError(f"media is {size} bytes, over the {MEDIA_LIMIT} byte limit")
    mime = meta.get("mime_type") or "application/octet-stream"
    url = meta.get("url")
    if not url:
        raise WhatsAppError("Meta returned no media URL.")
    s = get_settings()
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        resp = client.get(url, headers={"Authorization": f"Bearer {s.whatsapp_access_token}"})
    if resp.status_code >= 400:
        raise WhatsAppError(f"media download: HTTP {resp.status_code}")
    data = resp.content
    if len(data) > MEDIA_LIMIT:
        raise WhatsAppError(f"media is {len(data)} bytes, over the {MEDIA_LIMIT} byte limit")
    return data, mime, None


# ── Proactive notices and the 24-hour window ──────────────────────────────────────────


def window_open(last_in_at: datetime | None, now: datetime | None = None) -> bool:
    """True while Meta still allows a free-form message to this patient."""
    if not last_in_at:
        return False
    if last_in_at.tzinfo is None:  # Firestore hands back naive datetimes in some setups
        last_in_at = last_in_at.replace(tzinfo=UTC)
    return (now or datetime.now(UTC)) - last_in_at <= WINDOW


def send_template(to: str, params: list[str]) -> dict:
    """A pre-approved template, for when the 24-hour window has closed."""
    s = get_settings()
    if not s.whatsapp_template:
        raise WhatsAppError(
            "Outside WhatsApp's 24-hour window, so a template is needed: set WHATSAPP_TEMPLATE "
            "to a template approved in Meta Business Manager."
        )
    return _call(
        f"{s.whatsapp_phone_number_id}/messages",
        {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": s.whatsapp_template,
                "language": {"code": s.whatsapp_template_language},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": p[:1024]} for p in params],
                    }
                ],
            },
        },
    )


def send_notice(
    to: str, text: str, last_in_at: datetime | None, now: datetime | None = None
) -> str:
    """Send an unprompted update, choosing free-form or template by the window.

    Returns "text", "template" or "skipped" so the caller can log what happened instead of
    silently dropping a reminder.
    """
    if window_open(last_in_at, now):
        send_text(to, text)
        return "text"
    if not get_settings().whatsapp_template:
        log.warning("whatsapp notice skipped for %s: outside the 24h window and no template", to)
        return "skipped"
    send_template(to, [text[:1024]])
    return "template"
