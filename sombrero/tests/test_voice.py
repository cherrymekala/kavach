import array
import math
import re
import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from kavach.config import get_settings
from kavach.main import app
from kavach.models import Assessment, Case, CaseFacts
from kavach.routers import voice
from kavach.tools import audio, store

TOKEN = "test-token"


def _tone(n: int, rate: int, hz: float = 440, amp: int = 8000) -> bytes:
    return array.array(
        "h", (int(amp * math.sin(2 * math.pi * hz * i / rate)) for i in range(n))
    ).tobytes()


def test_ulaw_round_trip_keeps_speech_level_samples_close():
    pcm = _tone(800, 8000)
    back = array.array("h", audio.ulaw_to_pcm16(audio.pcm16_to_ulaw(pcm)))
    orig = array.array("h", pcm)
    # mu-law is logarithmic: error grows with amplitude but stays within ~3% of full scale.
    assert max(abs(a - b) for a, b in zip(orig, back)) < 1000
    assert audio.pcm16_to_ulaw(array.array("h", [0]).tobytes()) == b"\xff"


def test_resampling_lengths_match_the_rates():
    assert len(audio.phone_to_live(b"\xff" * 160)) == 320 * 2  # 20 ms: 160 -> 320 samples
    assert len(audio.live_to_phone(_tone(480, 24000))) == 160  # 20 ms at 24 kHz -> 160 bytes


@pytest.fixture
def phone(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("PUBLIC_URL", "https://kavach.example")
    monkeypatch.setenv("AUTH_DISABLED", "true")
    get_settings.cache_clear()
    store._memory.clear()
    case = Case(
        id="c1",
        owner="dev-user",
        facts=CaseFacts(policy_number="P/161100/01/2026/004512", insurer="Star Health"),
        assessment=Assessment(strength="strong", score=0.8),
    )
    store.save_case(case)
    yield TestClient(app)
    get_settings.cache_clear()


def _post(client, path: str, form: dict, sign: bool = True):
    url = f"https://kavach.example{path}"
    headers = {"X-Twilio-Signature": voice.twilio_signature(TOKEN, url, form)} if sign else {}
    return client.post(path, data=form, headers=headers)


def test_unsigned_webhooks_are_rejected(phone):
    assert _post(phone, "/voice/incoming", {"From": "+919999900001"}, sign=False).status_code == 403


def test_caller_must_key_the_last_four_policy_digits(phone):
    r = _post(phone, "/voice/incoming", {"From": "+919999900001"})
    assert r.status_code == 200 and "last four digits" in r.text
    action = re.search(r'action="([^"]+)"', r.text).group(1).replace("&amp;", "&")

    wrong = _post(phone, action, {"Digits": "1111"})
    assert "don't match" in wrong.text
    right = _post(phone, action, {"Digits": "4512"})
    assert "Press 1" in right.text and "Press 2" in right.text

    menu = re.search(r'action="([^"]+)"', right.text).group(1).replace("&amp;", "&")
    connect = _post(phone, menu, {"Digits": "2"})
    assert '<Stream url="wss://kavach.example/voice/stream">' in connect.text
    assert '<Parameter name="mode" value="rehearse"/>' in connect.text


def test_stream_links_are_signed_and_expire(phone):
    ts = str(int(time.time()))
    good = {
        "case": "c1",
        "mode": "status",
        "ts": ts,
        "sig": voice._sign("stream", "c1", "status", ts),
    }
    assert voice._authorise_stream(good)[1] == "status"
    for bad in (
        {**good, "case": "someone-else"},
        {**good, "mode": "rehearse"},
        {
            **good,
            "ts": str(int(ts) - 3600),
            "sig": voice._sign("stream", "c1", "status", str(int(ts) - 3600)),
        },
    ):
        with pytest.raises(HTTPException):
            voice._authorise_stream(bad)


def test_phone_status_prompt_leaves_out_identifying_details():
    case = Case(
        id="c",
        owner="u",
        facts=CaseFacts(
            patient_name="Lakshmi", policy_number="P/1", hospital="Sri Sai", insurer="Star Health"
        ),
    )
    from kavach.agents import voice as agent

    text = agent.status_instructions(case)
    assert "Star Health" in text
    for secret in ("Lakshmi", "P/1", "Sri Sai"):
        assert secret not in text
