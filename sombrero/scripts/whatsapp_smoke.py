"""See exactly what Kavach replies on WhatsApp — with no Meta app and no Gemini key.

Drives the real webhook endpoint in-process with correctly signed bodies, and prints the
outbound messages instead of sending them. Use it to check the copy and the flow before you
point Meta at the service, and to reproduce a bug report without involving Meta.

    cd <repo root>
    sombrero/.venv/bin/python sombrero/scripts/whatsapp_smoke.py

Nothing here touches the network: `AUTH_DISABLED` and `WHATSAPP_DRY_RUN` are set below, the
media download is stubbed, and the analysis is stubbed so no Gemini call is made.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Must be set before kavach is imported: settings are cached for the life of the process.
os.environ.update(
    {
        "AUTH_DISABLED": "true",
        "WHATSAPP_DRY_RUN": "true",
        "WHATSAPP_APP_SECRET": "smoke-app-secret",
        "WHATSAPP_VERIFY_TOKEN": "smoke-verify-token",
        "PACKS_DIR": str(ROOT / "magellan/packs"),
    }
)
sys.path.insert(0, str(ROOT / "sombrero/src"))

import hashlib
import hmac

from fastapi.testclient import TestClient

from kavach.main import app
from kavach.models import Assessment, CaseStatus, Letter
from kavach.routers import whatsapp as channel
from kavach.tools import store
from kavach.tools import whatsapp as wa

SECRET = os.environ["WHATSAPP_APP_SECRET"]
SENDER = "919493925966"  # what Meta sends: digits, no leading +
client = TestClient(app)
failures = []

outbound: list[str] = []


def _show(to: str, body: str) -> None:
    outbound.append(f"  -> to {to}:\n" + "\n".join(f"     {line}" for line in body.splitlines()))


def _show_media(to: str, data: bytes, filename: str, mime: str, caption=None) -> None:
    outbound.append(f"  -> to {to}: [document] {filename} ({len(data)} bytes) {caption or ''}")


def _step(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


def _check(label: str, ok: bool) -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        failures.append(label)


def _post(payload: dict, secret: str = SECRET):
    body = json.dumps(payload).encode()
    return client.post(
        "/whatsapp/webhook", content=body, headers={"X-Hub-Signature-256": _sign(body, secret)}
    )


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _text(body: str, mid: str) -> dict:
    return _envelope(
        {
            "from": SENDER,
            "id": mid,
            "timestamp": "1760000000",
            "type": "text",
            "text": {"body": body},
        }
    )


def _image(mid: str, caption: str) -> dict:
    return _envelope(
        {
            "from": SENDER,
            "id": mid,
            "timestamp": "1760000000",
            "type": "image",
            "image": {"id": "media-1", "mime_type": "image/jpeg", "caption": caption},
        }
    )


def _envelope(message: dict) -> dict:
    return {"entry": [{"changes": [{"value": {"messages": [message]}}]}]}


def main() -> int:
    # Capture outbound traffic and stub the two things that need a network.
    wa.send_text = _show
    wa.send_media = _show_media
    wa.download_media = lambda media_id: (b"\xff\xd8\xff\xe0fake-jpeg-bytes", "image/jpeg", None)
    channel.run_case = _stub_analysis

    _step("1. Meta's subscription handshake (GET /whatsapp/webhook)")
    good = client.get(
        "/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "smoke-verify-token",
            "hub.challenge": "1158201444",
        },
    )
    print(f"  right token -> {good.status_code} body={good.text!r}")
    _check("challenge echoed", good.status_code == 200 and good.text == "1158201444")
    bad = client.get(
        "/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1"},
    )
    _check("wrong verify token refused", bad.status_code == 403)

    _step("2. A body that is not signed with the app secret (POST /whatsapp/webhook)")
    forged = _post(_text("status", "wamid.forged"), secret="not-the-app-secret")
    print(f"  -> {forged.status_code} {forged.json()}")
    _check("forged webhook rejected", forged.status_code == 403)

    _step("3. The patient says hello (no case yet)")
    _post(_text("hi", "wamid.1"))
    _flush()

    _step("4. The patient sends a photo of the rejection letter")
    _post(_image("wamid.2", "My claim rejection"))
    case = store.list_cases("dev-user")[0]
    _check("a case was created", case is not None)
    _check("country guessed from +91", case.country == "IN")
    _check("the photo was stored", [d.filename for d in case.documents] == ["whatsapp.jpg"])
    _flush()

    _step("5. The patient attaches the policy PDF")
    _post(
        _envelope(
            {
                "from": SENDER,
                "id": "wamid.3",
                "timestamp": "1760000000",
                "type": "document",
                "document": {
                    "id": "media-2",
                    "mime_type": "application/pdf",
                    "filename": "policy.pdf",
                },
            }
        )
    )
    _check("two documents on the case", len(store.load_case(case.id).documents) == 2)
    _flush()

    _step("6. The patient asks for the analysis")
    _post(_text("ANALYSE", "wamid.4"))
    _flush()

    _step("7. The patient asks where things stand")
    _post(_text("status", "wamid.5"))
    _flush()

    _step("8. The patient asks for the appeal letter")
    _post(_text("letter", "wamid.6"))
    _flush()

    _step("9. Meta redelivers message wamid.5 (it did not get a fast 200)")
    before = len(outbound)
    _post(_text("status", "wamid.5"))
    _check("redelivery ignored", len(outbound) == before)

    _step("10. The patient deletes their data")
    _post(_text("delete", "wamid.7"))
    _flush()
    _check("case kept until confirmed", store.load_case(case.id) is not None)
    _post(_text("DELETE YES", "wamid.8"))
    _flush()
    _check("case erased after confirmation", store.load_case(case.id) is None)

    print()
    if failures:
        print(f"\033[31m{len(failures)} check(s) failed:\033[0m " + "; ".join(failures))
        return 1
    print("\033[32mAll checks passed.\033[0m")
    return 0


def _stub_analysis(case_id: str) -> None:
    """Stand in for the Gemini pipeline so the smoke run needs no credentials."""
    case = store.load_case(case_id)
    case.assessment = Assessment(strength="strong", score=0.82, arguments=[], missing_documents=[])
    case.letter = Letter(
        subject="Appeal against claim rejection", english="Dear Sir,", language="en"
    )
    case.status = CaseStatus.READY
    store.save_case(case)


def _flush() -> None:
    for line in outbound:
        print(f"\033[36m{line}\033[0m")
    outbound.clear()


if __name__ == "__main__":
    raise SystemExit(main())
