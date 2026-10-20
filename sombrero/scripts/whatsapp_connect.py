"""Connect the WhatsApp channel: turn one Meta ID into a working, tested channel.

You only have to find ONE value in Meta's dashboard — either the WhatsApp Business Account ID
or the phone number ID. This figures out which one you pasted, finds the phone number behind it,
writes it to the repo-root `.env`, and proves it works.

    # you pasted the WABA ID from Business settings (easiest to find)
    python sombrero/scripts/whatsapp_connect.py --id 123456789012345

    # you pasted the phone number ID from API Setup
    python sombrero/scripts/whatsapp_connect.py --id 987654321098765

    # also send a real message to prove it end to end
    python sombrero/scripts/whatsapp_connect.py --id 123456789012345 --send +919493925966

Reads WHATSAPP_ACCESS_TOKEN and WHATSAPP_APP_SECRET from the repo-root `.env` (or the
environment). Nothing is sent unless you pass --send.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sombrero/src"))

import httpx

from kavach.config import get_settings

GRAPH = "https://graph.facebook.com"
ENV = ROOT / ".env"

# Phone-number nodes expose these; a WABA does not.
PHONE_FIELDS = (
    "id,display_phone_number,verified_name,quality_rating,platform_type,code_verification_status"
)
WABA_FIELDS = "id,name,currency,timezone_id,account_review_status"

HINTS = {
    190: "The access token is invalid or expired. Generate a new one (System user → Generate token).",
    200: "The token lacks whatsapp_business_messaging. Add the permission and regenerate it.",
    100: "Meta rejected the ID or field — usually a wrong ID, or the app has no access to it.",
    10: "The app does not have permission for this action: the WhatsApp product is not "
    "available to it, or the asset is not assigned to your system user.",
    131030: "That recipient is not on the test number's allowed list (WhatsApp → API Setup → To).",
    131047: "Re-engagement: Meta only allows free-form messages within 24h of the patient's "
    "last message. The token and phone number ID are FINE — message the number first.",
}


def die(message: str) -> None:
    print(f"\033[31m{message}\033[0m")
    raise SystemExit(1)


def explain(resp: httpx.Response) -> str:
    try:
        err = resp.json()["error"]
    except Exception:  # noqa: BLE001
        return f"HTTP {resp.status_code}: {resp.text[:300]}"
    code = err.get("code")
    hint = HINTS.get(code, err.get("error_user_msg") or "")
    return f"[{code}] {err.get('message')}" + (f"\n      → {hint}" if hint else "")


def call(path: str, token: str, **params) -> httpx.Response:
    params["access_token"] = token
    return httpx.get(
        f"{GRAPH}/{get_settings().whatsapp_api_version}/{path}", params=params, timeout=30
    )


def phone_numbers(waba: str, token: str) -> list[dict]:
    r = call(f"{waba}/phone_numbers", token, fields=PHONE_FIELDS)
    if r.status_code >= 400:
        print(f"  GET /{waba}/phone_numbers failed:\n    {explain(r)}")
        return []
    return r.json().get("data") or []


def remember(phone_id: str) -> None:
    """Write WHATSAPP_PHONE_NUMBER_ID into the repo-root .env, leaving everything else alone."""
    if not ENV.exists():
        print(f"  (no {ENV}; set WHATSAPP_PHONE_NUMBER_ID in your environment instead)")
        return
    lines = ENV.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith("WHATSAPP_PHONE_NUMBER_ID="):
            lines[i] = f"WHATSAPP_PHONE_NUMBER_ID={phone_id}"
            break
    else:
        lines.append(f"WHATSAPP_PHONE_NUMBER_ID={phone_id}")
    ENV.write_text("\n".join(lines) + "\n")
    print(f"  saved WHATSAPP_PHONE_NUMBER_ID={phone_id} to {ENV.name}")


def send(phone_id: str, token: str, to: str) -> bool:
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "+" + "".join(c for c in to if c.isdigit()),
        "type": "text",
        "text": {"preview_url": False, "body": "Kavach setup check: this channel is live."},
    }
    r = httpx.post(
        f"{GRAPH}/{get_settings().whatsapp_api_version}/{phone_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"\n\033[31mSend failed\033[0m\n    {explain(r)}")
        return False
    msg_id = (r.json().get("messages") or [{}])[0].get("id")
    print(f"\n\033[32mSent.\033[0m message id {msg_id} — check the phone.")
    return True


def candidates(raw: list[str]) -> list[str]:
    """Every 6+ digit token in the arguments, in order, without duplicates."""
    out: list[str] = []
    for chunk in raw:
        for token in re.split(r"[\s,;]+", chunk):
            token = token.strip()
            if token.isdigit() and len(token) >= 6 and token not in out:
                out.append(token)
    return out


def resolve(ids: list[str], token: str, prefer: str | None = None) -> tuple[str, dict] | None:
    """Pick the phone number out of a pile of candidate ids.

    Pasted ids are usually a mix of app ids, business ids and the ones we want, and they all
    look alike. Probe each: a WABA is preferred (it leads to its numbers), otherwise a phone
    number id is used directly.
    """
    phones: list[tuple[str, dict]] = []
    want = re.sub(r"\D", "", prefer or "")
    for node_id in ids:
        r = call(node_id, token, fields=WABA_FIELDS)
        if r.status_code == 200:
            name = r.json().get("name")
            print(f"  {node_id}: WhatsApp Business Account ({name})")
            numbers = phone_numbers(node_id, token)
            for n in numbers:
                print(
                    f"      {n.get('id')}  {n.get('display_phone_number')}  {n.get('verified_name')}"
                    f"  verified={n.get('code_verification_status')}"
                )
                phones.append((node_id, n))
            if not numbers:
                print("      (no phone numbers on this WABA yet)")
            continue

        r = call(node_id, token, fields=PHONE_FIELDS)
        if r.status_code == 200:
            n = r.json()
            print(f"  {node_id}: phone number ({n.get('display_phone_number')})")
            phones.append((node_id, n))
            continue

        print(f"  {node_id}: not a WABA or a phone number this token can read")

    if want:
        matching = [
            p for p in phones if want in re.sub(r"\D", "", p[1].get("display_phone_number") or "")
        ]
        if matching:
            return matching[0]
        if phones:
            print(f"  none of the numbers above contains {prefer}; using the first")
    return phones[0] if phones else None


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Connect WhatsApp from one or more Meta ids (paste as many as you like)."
    )
    ap.add_argument(
        "--id",
        required=True,
        nargs="+",
        help="WABA id, phone number id, or a whole list — the right one is picked for you",
    )
    ap.add_argument("--number", help="prefer the phone number whose display number contains this")
    ap.add_argument("--send", metavar="+91…", help="send a real test message to this number")
    ap.add_argument("--token", help="override WHATSAPP_ACCESS_TOKEN")
    args = ap.parse_args()

    s = get_settings()
    token = args.token or s.whatsapp_access_token
    if not token:
        die("No access token. Put WHATSAPP_ACCESS_TOKEN in the repo-root .env.")

    ids = candidates(args.id)
    if not ids:
        die("No numeric ids found in those arguments.")

    print(f"WhatsApp connect — {len(ids)} candidate id(s)\n")
    found = resolve(ids, token, args.number)
    if not found:
        die(
            "\nNone of those ids is a WhatsApp Business Account or phone number this token can "
            "read.\n  → Check the token belongs to the app that owns the WhatsApp number, and "
            "that the WhatsApp account is assigned to the system user."
        )

    _, info = found
    phone_id = info["id"]
    print(f"\n  chosen: {info.get('display_phone_number')} → {phone_id}")
    remember(phone_id)
    ok = send(phone_id, token, args.send) if args.send else True
    print("\nDone." if ok else "\nConfigured, but the send failed.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
