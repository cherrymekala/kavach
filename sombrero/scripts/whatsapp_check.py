"""Preflight for the WhatsApp channel: tells you which setting is wrong, and what to do.

Run it after each step of the Meta setup. Every check prints PASS / WARN / FAIL plus the exact
place to fix it, so you never have to guess whether the token, the phone number id or the app
secret is the thing that is broken.

    cd <repo root>

    # 1. Are the values present and the right shape? (no network)
    python sombrero/scripts/whatsapp_check.py

    # 2. Does Meta accept the token and the phone number id?
    python sombrero/scripts/whatsapp_check.py --live

    # 3. Prove the deployed service has the same verify token and app secret
    python sombrero/scripts/whatsapp_check.py --webhook https://sombrero-urb5ttky3q-el.a.run.app

    # 4. Send a real message (only works to a verified recipient, on a test number)
    python sombrero/scripts/whatsapp_check.py --live --send +919493925966

Values are read through `kavach.config`, so this checks exactly what the app will see —
including the repo-root `.env`.
"""

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sombrero/src"))
# Packs and storage are irrelevant here, but config reads the repo-root .env like the app does.
os.environ.setdefault("PACKS_DIR", str(ROOT / "magellan/packs"))

import httpx

from kavach.config import get_settings

OK, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"
results: list[tuple[str, str, str]] = []  # (level, what, what to do)

# Meta's error codes, mapped to the setting that is actually wrong.
ERRORS = {
    190: (
        "The access token is invalid or has expired. A token from WhatsApp → API Setup is "
        "temporary (hours). Create a permanent one with a Business system user."
    ),
    200: (
        "The token is missing the whatsapp_business_messaging permission. Add it to the "
        "system user's assigned assets, then regenerate the token."
    ),
    100: (
        "Meta rejected a parameter — usually a wrong WHATSAPP_PHONE_NUMBER_ID. Copy the "
        "'Phone number ID' (not the phone number itself) from WhatsApp → API Setup."
    ),
    131030: (
        "The recipient is not in the test number's allowed list. Add it under WhatsApp → "
        "API Setup → 'To' and verify the code Meta sends."
    ),
    131047: (
        "Re-engagement: Meta only allows a free-form message within 24 hours of the patient's "
        "last message. The token and phone number id are FINE — message the number first, or "
        "set WHATSAPP_TEMPLATE for reminders."
    ),
    132001: "The template name or language does not exist in this WhatsApp Business Account.",
}


def record(level: str, what: str, fix: str = "") -> None:
    results.append((level, what, fix))


def shape_checks() -> None:
    """Everything that can be checked with no network and no Meta account."""
    s = get_settings()

    if not s.whatsapp_phone_number_id:
        record(
            FAIL,
            "WHATSAPP_PHONE_NUMBER_ID is not set",
            "Meta app → WhatsApp → API Setup → 'Phone number ID'. It is a long number, and it "
            "is NOT the phone number you message.",
        )
    elif not s.whatsapp_phone_number_id.isdigit():
        record(
            FAIL,
            f"WHATSAPP_PHONE_NUMBER_ID is not all digits ({s.whatsapp_phone_number_id!r})",
            "Paste only the id. If you copied a phone number, take the 'Phone number ID' instead.",
        )
    else:
        record(OK, f"WHATSAPP_PHONE_NUMBER_ID present ({s.whatsapp_phone_number_id})")

    if not s.whatsapp_access_token:
        record(
            FAIL,
            "WHATSAPP_ACCESS_TOKEN is not set",
            "Meta Business settings → System users → your system user → Generate token, with the "
            "whatsapp_business_messaging permission.",
        )
    else:
        record(OK, f"WHATSAPP_ACCESS_TOKEN present ({len(s.whatsapp_access_token)} characters)")
        record(
            INFO,
            "A token's lifetime cannot be seen from its shape",
            "Run with --live: that is what proves it is still valid.",
        )

    secret = s.whatsapp_app_secret
    if not secret:
        record(
            FAIL,
            "WHATSAPP_APP_SECRET is not set",
            "Meta app → App settings → Basic → App secret. Without it we cannot prove an "
            "incoming webhook came from Meta, and every webhook will be rejected with 403.",
        )
    elif not re.fullmatch(r"[0-9a-f]{32}", secret):
        record(
            FAIL,
            "WHATSAPP_APP_SECRET does not look like an app secret (expected 32 hex characters)",
            "Copy App settings → Basic → App secret. Do not paste the client token or an "
            "access token here.",
        )
    else:
        record(OK, "WHATSAPP_APP_SECRET present (32 hex characters)")

    if not s.whatsapp_verify_token:
        record(FAIL, "WHATSAPP_VERIFY_TOKEN is empty", "Set any random string.")
    elif s.whatsapp_verify_token == "kavach-verify":
        record(
            WARN,
            "WHATSAPP_VERIFY_TOKEN is still the default 'kavach-verify'",
            "Use a random value in both cloudbuild.yaml and Meta's webhook setup. The value is "
            "guessable, and guessing it only grants the subscription challenge — but change it "
            "anyway.",
        )
    else:
        record(OK, "WHATSAPP_VERIFY_TOKEN is set and not the default")

    if s.whatsapp_template:
        record(OK, f"WHATSAPP_TEMPLATE set ({s.whatsapp_template})")
        record(
            INFO,
            "Template presence cannot be checked without the WhatsApp Business Account id",
            "Meta app → WhatsApp → Message templates: confirm the name and language match, and "
            "that its status is Approved.",
        )
    else:
        record(
            INFO,
            "WHATSAPP_TEMPLATE is not set",
            "Fine to start with. Reminders sent more than 24 hours after the patient's last "
            "message will be logged and skipped instead of delivered.",
        )

    # Local-mode switches that make a "successful" test meaningless.
    if s.auth_disabled:
        record(
            WARN,
            "AUTH_DISABLED=true: cases live in memory and every caller is 'dev-user'",
            "Expected locally. Never set this on Cloud Run — there, WhatsApp identifies the "
            "patient by their phone number, which needs real Firebase.",
        )
    if s.whatsapp_dry_run:
        record(
            WARN,
            "WHATSAPP_DRY_RUN=true: outbound messages are logged, not sent",
            "Expected locally. Remove it (or set false) to send for real.",
        )


def _get(s, path: str, params: dict | None = None) -> httpx.Response:
    url = f"https://graph.facebook.com/{s.whatsapp_api_version}/{path}"
    return httpx.get(
        url,
        headers={"Authorization": f"Bearer {s.whatsapp_access_token}"},
        params=params,
        timeout=30,
    )


def _explain(resp: httpx.Response) -> str:
    try:
        error = resp.json()["error"]
    except Exception:  # noqa: BLE001 - print whatever came back
        return f"HTTP {resp.status_code}: {resp.text[:300]}"
    code = error.get("code")
    message = error.get("message", "")
    hint = ERRORS.get(code)
    return f"[{code}] {message}" + (f"\n      → {hint}" if hint else "")


def live_checks(send_to: str | None) -> None:
    """Prove the token and phone number id work, then optionally send a real message."""
    s = get_settings()
    if not (s.whatsapp_access_token and s.whatsapp_phone_number_id):
        record(
            FAIL,
            "--live needs WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID",
            "Fix the above first.",
        )
        return

    resp = _get(
        s,
        s.whatsapp_phone_number_id,
        {"fields": "display_phone_number,verified_name,quality_rating,platform_type"},
    )
    if resp.status_code >= 400:
        record(FAIL, "Meta rejected the token/phone-number-id pair", _explain(resp))
    else:
        data = resp.json()
        record(
            OK,
            f"Meta accepted the pair: {data.get('display_phone_number')} "
            f"({data.get('verified_name')}, quality {data.get('quality_rating')})",
        )
        record(
            INFO,
            "Patients message this display number",
            "Put it in the web app's VITE_WHATSAPP_NUMBER (digits only, no '+').",
        )

    if not send_to:
        record(
            INFO,
            "Add --send +91xxxxxxxxxx to try a real message",
            "Only verified recipients work on a test number.",
        )
        return

    to = "+" + "".join(ch for ch in send_to if ch.isdigit())
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": "Kavach setup check: this channel is live."},
    }
    resp = httpx.post(
        f"https://graph.facebook.com/{s.whatsapp_api_version}/{s.whatsapp_phone_number_id}/messages",
        headers={"Authorization": f"Bearer {s.whatsapp_access_token}"},
        json=body,
        timeout=30,
    )
    if resp.status_code >= 400:
        record(FAIL, f"Could not send to {to}", _explain(resp))
    else:
        record(
            OK, f"Sent a real message to {to} (id {resp.json().get('messages', [{}])[0].get('id')})"
        )
        record(
            INFO,
            "Check the phone",
            "If it arrived, the token, the id and the recipient list are all correct.",
        )


def webhook_checks(base: str) -> None:
    """Compare the deployed service against the local settings, with no side effects.

    The POST bodies carry no `messages`, so the service verifies the signature and then does
    nothing — nothing is sent to any patient.
    """
    s = get_settings()
    url = f"{base.rstrip('/')}/whatsapp/webhook"
    challenge = "kavach-preflight-42"

    try:
        resp = httpx.get(
            url,
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": s.whatsapp_verify_token,
                "hub.challenge": challenge,
            },
            timeout=30,
        )
    except httpx.HTTPError as exc:
        record(
            FAIL, f"Could not reach {url}", f"{exc}\n      → Is the service deployed at this URL?"
        )
        return

    if resp.status_code == 200 and resp.text.strip() == challenge:
        record(OK, "The deployed service answers the subscription challenge with our verify token")
    elif resp.status_code == 403:
        record(
            FAIL,
            "The deployed service rejected our verify token (403)",
            "It has a different WHATSAPP_VERIFY_TOKEN. Set _WHATSAPP_VERIFY_TOKEN in "
            "cloudbuild.yaml to this value, or paste the deployed value into Meta's webhook setup.",
        )
    elif resp.status_code == 404:
        record(
            FAIL,
            "No /whatsapp/webhook on the deployed service (404)",
            "Deploy the branch that adds it.",
        )
    else:
        record(FAIL, f"Unexpected reply to the challenge: HTTP {resp.status_code}", resp.text[:300])

    if not s.whatsapp_app_secret:
        record(
            FAIL,
            "Skipping the signature checks: no local WHATSAPP_APP_SECRET",
            "Set it, then run again.",
        )
        return

    # A body with no messages: the signature is verified, then the handler has nothing to do.
    body = json.dumps({"entry": [{"changes": [{"value": {"statuses": []}}]}]}).encode()

    def post(secret: str) -> httpx.Response:
        signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return httpx.post(url, content=body, headers={"X-Hub-Signature-256": signature}, timeout=30)

    # Forged first: if the service accepts a signature that cannot be Meta's, then a matching
    # secret proves nothing, and reporting "accepts our app secret" would be false comfort.
    forged = post("definitely-not-the-app-secret")
    trustworthy = forged.status_code == 403
    if trustworthy:
        record(OK, "A forged signature is rejected, so Meta's signature is really being checked")
    else:
        record(
            FAIL,
            f"A forged signature was ACCEPTED (HTTP {forged.status_code})",
            "Anyone could POST fake messages. Set WHATSAPP_APP_SECRET on the deployed service — "
            "with no app secret it trusts every caller while AUTH_DISABLED=true, which must never "
            "be on in production.",
        )

    good = post(s.whatsapp_app_secret)
    if not trustworthy:
        record(
            INFO,
            "So the app-secret comparison is inconclusive",
            "Fix the forged-signature failure first, then run this again.",
        )
    elif good.status_code == 200:
        record(
            OK,
            "The deployed service accepts our app secret (Meta's real webhooks will be accepted)",
        )
    elif good.status_code == 403:
        record(
            FAIL,
            "The deployed service rejected a body signed with our app secret (403)",
            "Its WHATSAPP_APP_SECRET differs. Put the app secret in Secret Manager as "
            "whatsapp-app-secret, then redeploy.",
        )
    else:
        record(FAIL, f"Unexpected reply to a signed body: HTTP {good.status_code}", good.text[:300])


def report() -> int:
    print()
    for level, what, fix in results:
        colour = {OK: "\033[32m", WARN: "\033[33m", FAIL: "\033[31m", INFO: "\033[36m"}[level]
        print(f"{colour}{level:4}\033[0m  {what}")
        if fix:
            print(f"        {fix}")
    failed = sum(1 for level, _, _ in results if level == FAIL)
    warned = sum(1 for level, _, _ in results if level == WARN)
    print()
    if failed:
        print(f"\033[31m{failed} check(s) failed.\033[0m Fix those, then run this again.")
        return 1
    print(
        "\033[32mAll required settings are in place.\033[0m"
        + (f" ({warned} warning(s))" if warned else "")
    )
    print("Next: message the display number from the patient's phone and check the reply.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the WhatsApp setup.")
    parser.add_argument(
        "--live", action="store_true", help="call the Graph API to prove the token works"
    )
    parser.add_argument(
        "--send", metavar="+91…", help="send a real message to this number (with --live)"
    )
    parser.add_argument(
        "--webhook", metavar="URL", help="the deployed base URL, e.g. https://…run.app"
    )
    args = parser.parse_args()

    print("WhatsApp setup check")
    shape_checks()
    if args.live or args.send:
        live_checks(args.send)
    if args.webhook:
        webhook_checks(args.webhook)
    if not (args.live or args.send or args.webhook):
        print("\n(offline checks only — add --live and --webhook to test the real setup)")
    return report()


if __name__ == "__main__":
    raise SystemExit(main())
