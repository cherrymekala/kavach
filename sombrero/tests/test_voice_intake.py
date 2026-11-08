import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import HTTPException

from kavach.agents import voice_intake
from kavach.models import Case, CaseKind, CaseStatus
from kavach.routers import voice_intake as relay
from kavach.tools import store


def _case(**kw) -> Case:
    case = Case(id=uuid.uuid4().hex, owner="dev-user", country="IN", language="hi", **kw)
    store.save_case(case)
    return case


def test_the_interviewer_speaks_the_patients_language_and_never_asks_for_identifiers():
    text = voice_intake.instructions(
        Case(id="x", owner="u", language="ta", kind=CaseKind.PRE_DISCHARGE)
    )
    assert "Speak Tamil" in text and "daily rent" in text
    assert "Never ask for names, phone numbers, addresses, or policy, claim or ID numbers" in text
    assert "rejected or cut" in voice_intake.instructions(Case(id="x", owner="u"))
    assert voice_intake.live_config(
        Case(id="x", owner="u", language="hi")
    ).input_audio_transcription.language_codes == [
        "en-IN",
        "hi-IN",
    ]


def test_chunks_merge_per_speaker_and_the_transcript_is_marked_automatic():
    talk = relay._Talk()
    for who, text in [
        ("ai", "Namaste. "),
        ("ai", "What happened?"),
        ("you", "My claim for "),
        ("you", "gallstones was rejected."),
    ]:
        talk.add(who, text)
    assert talk.lines == [
        ("ai", "Namaste. What happened?"),
        ("you", "My claim for gallstones was rejected."),
    ]
    text = voice_intake.transcript(
        talk.lines,
        Case(id="x", owner="u", language="hi"),
        datetime(2026, 11, 8, 10, 30, tzinfo=UTC),
    )
    assert text.startswith(
        "Patient's account, told by voice to Kavach on 08 Nov 2026 10:30 UTC (Hindi)."
    )
    assert "Transcribed automatically" in text
    assert "Kavach: Namaste. What happened?\nPatient: My claim for gallstones was rejected." in text


def test_a_real_account_is_saved_to_the_case_and_a_greeting_is_not(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    case = _case()
    hello = relay._Talk()
    hello.add("ai", "What happened?")
    hello.add("you", "Hello hello.")
    assert relay._save(case.id, hello) is None and store.load_case(case.id).documents == []

    talk = relay._Talk()
    talk.add("ai", "What happened?")
    talk.add(
        "you", "Star Health rejected my claim for gallbladder surgery saying it was pre-existing."
    )
    doc = relay._save(case.id, talk)
    saved = store.load_case(case.id)
    assert doc is not None and saved.documents[-1].filename.startswith("spoken-account-")
    assert saved.events[-1].kind == "voice_intake"
    assert "pre-existing" in Path(doc.gcs_uri).read_text(encoding="utf-8")


def test_cases_already_being_analysed_cannot_start_a_voice_intake():
    case = _case(status=CaseStatus.ANALYSING)
    with pytest.raises(HTTPException) as exc:
        relay._authorise({"token": None}, case.id)
    assert exc.value.status_code == 409


def test_a_failed_live_session_tells_the_patient_instead_of_hanging(monkeypatch):
    from fastapi.testclient import TestClient

    from kavach.agents import hearing
    from kavach.main import app

    case = _case()

    class Exhausted:
        class aio:
            class live:
                @staticmethod
                def connect(**kw):
                    raise RuntimeError("1011 Resource exhausted")

    monkeypatch.setattr(hearing, "client", lambda: Exhausted)
    with TestClient(app).websocket_connect(f"/cases/{case.id}/voice-intake") as ws:
        ws.send_json({"token": None})
        assert ws.receive_json() == {"error": relay.BUSY}
        assert ws.receive_json() == {"saved": None}
