import asyncio
import json
import logging

import pytest
from fastapi.testclient import TestClient

from kavach import logs
from kavach.agents import quality
from kavach.config import get_settings
from kavach.main import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # local uploads land in a temp folder
    get_settings.cache_clear()
    yield TestClient(app, raise_server_exceptions=False)
    get_settings.cache_clear()


def _upload(client, name: str) -> dict:
    case_id = client.post("/cases", json={"country": "IN"}).json()["id"]
    return client.post(
        f"/cases/{case_id}/documents", files={"file": (name, b"\xff\xd8 photo")}
    ).json()


def test_bad_photo_is_flagged_at_upload(client, monkeypatch):
    monkeypatch.setattr(quality, "check_photo", lambda uri: quality.PhotoIssue.BLURRY)
    assert _upload(client, "letter.jpg")["quality"] == "blurry"


def test_good_photos_and_pdfs_carry_no_warning(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        quality, "check_photo", lambda uri: calls.append(uri) or quality.PhotoIssue.OK
    )
    assert _upload(client, "letter.png")["quality"] is None
    assert _upload(client, "policy.pdf")["quality"] is None
    assert len(calls) == 1  # the PDF was never sent to the model


def test_photo_check_failure_never_blocks_the_upload(client, monkeypatch):
    def broken(uri):
        raise RuntimeError("402 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(quality, "check_photo", broken)
    doc = _upload(client, "letter.webp")
    assert doc["quality"] is None and doc["filename"] == "letter.webp"


def test_errors_are_written_for_error_reporting(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "sombrero")
    monkeypatch.setenv("K_REVISION", "sombrero-00042")
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            "kavach", logging.ERROR, __file__, 1, "coaching failed", None, None
        )
        import sys

        record.exc_info = sys.exc_info()
    entry = json.loads(logs.CloudRunFormatter().format(record))
    assert entry["severity"] == "ERROR"
    assert entry["@type"].endswith("ReportedErrorEvent")
    assert "ValueError: boom" in entry["message"] and "Traceback" in entry["message"]
    assert entry["serviceContext"] == {"service": "sombrero", "version": "sombrero-00042"}

    info = logging.LogRecord("kavach", logging.INFO, __file__, 1, "upload ok", None, None)
    assert "@type" not in json.loads(logs.CloudRunFormatter().format(info))


def test_unhandled_errors_get_a_friendly_500_and_one_error_log(client, caplog):
    def boom():
        raise RuntimeError("unexpected")

    app.add_api_route("/__boom", boom)
    with caplog.at_level(logging.ERROR):
        r = client.get("/__boom")
    assert r.status_code == 500
    assert r.json() == {"detail": "Something went wrong on our side. Please try again."}
    errors = [rec for rec in caplog.records if rec.levelno >= logging.ERROR and rec.exc_info]
    assert len(errors) == 1, [rec.name for rec in errors]


def test_background_task_failures_are_logged(caplog):
    async def run():
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(logs.log_task_exception)

        async def fails():
            raise RuntimeError("coaching exploded")

        task = loop.create_task(fails())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        loop.call_exception_handler(
            {
                "message": "Task exception was never retrieved",
                "exception": task.exception(),
                "task": task,
            }
        )

    with caplog.at_level(logging.ERROR):
        asyncio.run(run())
    assert any(rec.name == "kavach.tasks" and rec.exc_info for rec in caplog.records)
