"""Web push through Firebase Cloud Messaging: tracker reminders reach the patient's phone.

Best-effort like WhatsApp: a failed push never fails the daily tick or an inbound reply.
Tokens the browser has revoked (UNREGISTERED) are pruned so we stop sending to them.
"""

import logging

from ..config import get_settings
from ..models import Case
from . import store

log = logging.getLogger(__name__)

TITLE = "Kavach: your claim"


def _send(tokens: list[str], title: str, body: str, link: str) -> list[bool | str]:
    """Send one notification to each token. Returns True per success, "gone" for dead tokens."""
    from firebase_admin import exceptions, get_app, initialize_app, messaging

    try:
        get_app()
    except ValueError:
        initialize_app()
    message = messaging.MulticastMessage(
        tokens=tokens,
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                title=title, body=body, icon="/icons/icon-192.png", tag="kavach-tracker"
            ),
            fcm_options=messaging.WebpushFCMOptions(link=link),
        ),
    )
    result = messaging.send_each_for_multicast(message)
    out: list[bool | str] = []
    for r in result.responses:
        if r.success:
            out.append(True)
        elif isinstance(
            r.exception,
            (
                messaging.UnregisteredError,
                messaging.SenderIdMismatchError,
                exceptions.InvalidArgumentError,
            ),
        ):
            out.append("gone")
        else:
            out.append(False)
    return out


def notify_case(case: Case, text: str) -> int:
    """Push `text` to every device the owner and helpers turned reminders on for."""
    tokens = [t for uid in {case.owner, *case.helper_ids} for t in store.push_tokens_for(uid)]
    if not tokens:
        return 0
    link = f"{get_settings().app_url}/case/{case.id}"
    try:
        results = _send(tokens, TITLE, text, link)
    except Exception:
        log.warning("push: sending to case %s failed", case.id, exc_info=True)
        return 0
    for token, ok in zip(tokens, results, strict=False):
        if ok == "gone":
            store.delete_push_token(token)
    return sum(1 for ok in results if ok is True)
