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
