from fastapi.testclient import TestClient

from kavach.agents import hearing
from kavach.config import get_settings
from kavach.main import app
from kavach.models import Argument, Assessment, Case, CaseFacts, Source


def _case(country: str, language: str = "en") -> Case:
    return Case(
        id="h",
        owner="u",
        country=country,
        language=language,
        facts=CaseFacts(insurer="AIA Singapore", rejection_reason="non-disclosure of eczema"),
        assessment=Assessment(
            strength="strong",
            score=0.8,
            arguments=[
                Argument(
                    claim="Minor unrelated condition",
                    explanation="",
                    sources=[Source(kind="regulation", ref="MAS PQ para 3", quote="material")],
                )
            ],
        ),
    )


def test_instructions_use_the_country_dispute_body_language_and_case():
    sg = hearing.instructions(_case("SG", "zh"))
    assert "FIDReC" in sg and "Mandarin Chinese" in sg
    assert "non-disclosure of eczema" in sg and "MAS PQ para 3: material" in sg
    assert "Insurance Ombudsman" in hearing.instructions(_case("IN"))


def test_hearing_socket_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    get_settings.cache_clear()
    try:
        with TestClient(app).websocket_connect("/cases/x/hearing") as ws:
            ws.send_json({"token": None})
            assert "error" in ws.receive_json()
    finally:
        get_settings.cache_clear()


def test_unknown_facts_are_marked_so_the_model_does_not_invent_them():
    text = hearing.instructions(_case("IN"))
    assert '"policy_start": "unknown"' in text and "Never state or assume" in text


def test_speech_recognition_is_told_which_languages_to_expect():
    assert hearing.speech_languages(_case("IN", "hi")) == ["en-IN", "hi-IN"]
    assert hearing.speech_languages(_case("SG", "zh")) == ["en-SG", "cmn-CN"]
    assert hearing.speech_languages(_case("IN")) == ["en-IN"]
    config = hearing.live_config(_case("IN", "ta"))
    assert config.input_audio_transcription.language_codes == ["en-IN", "ta-IN"]


def test_fillers_are_not_scored_as_answers():
    assert not hearing.is_answer("Yeah, sure.")
    assert not hearing.is_answer("  um  ")
    assert hearing.is_answer("I was diagnosed in July 2026.")


def test_failed_coaching_tells_the_browser_instead_of_hanging(monkeypatch):
    import asyncio

    from kavach.routers import hearing as router

    def broken(*_args):
        raise RuntimeError("402 RESOURCE_EXHAUSTED")

    class FakeSocket:
        def __init__(self):
            self.sent = []

        async def send_json(self, msg):
            self.sent.append(msg)

    monkeypatch.setattr(hearing, "coach", broken)
    ws, turns = FakeSocket(), router._Turns()
    asyncio.run(router._coach(ws, _case("IN"), turns, "When were you diagnosed?", "In July 2026."))
    assert ws.sent == [{"coach_error": {"answer": "In July 2026."}}]
    assert turns.scores == []


def _live_case() -> Case:
    import uuid

    from kavach.tools import store

    case = _case("IN").model_copy(update={"id": uuid.uuid4().hex, "owner": "dev-user"})
    store.save_case(case)
    return case


def test_a_live_failure_before_any_answer_tells_the_patient(monkeypatch):
    from kavach.routers import hearing as relay

    case = _live_case()

    class Exhausted:
        class aio:
            class live:
                @staticmethod
                def connect(**kw):
                    raise RuntimeError("1011 Resource exhausted")

    monkeypatch.setattr(hearing, "client", lambda: Exhausted)
    with TestClient(app).websocket_connect(f"/cases/{case.id}/hearing") as ws:
        ws.send_json({"token": None})
        assert ws.receive_json() == {"error": relay.BUSY}


def test_a_live_failure_mid_rehearsal_still_debriefs_and_logs_it(monkeypatch):
    from kavach.routers import hearing as relay
    from kavach.tools import store

    case = _live_case()

    class Session:
        async def send_client_content(self, **kw):
            pass

    class Connection:
        async def __aenter__(self):
            return Session()

        async def __aexit__(self, *exc):
            return False

    class Client:
        class aio:
            class live:
                @staticmethod
                def connect(**kw):
                    return Connection()

    async def dies_after_one_answer(ws, session, case, turns):
        turns.answers = 1
        raise RuntimeError("1011 Resource exhausted")

    monkeypatch.setattr(hearing, "client", lambda: Client)
    monkeypatch.setattr(relay, "_from_gemini", dies_after_one_answer)
    with TestClient(app).websocket_connect(f"/cases/{case.id}/hearing") as ws:
        ws.send_json({"token": None})
        assert ws.receive_json() == {"error": relay.BUSY}
        assert set(ws.receive_json()["done"]) == {"summary", "top_tips", "average_score"}
    assert store.load_case(case.id).events[-1].kind == "rehearsal"
