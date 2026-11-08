"""WebSocket relay for voice-first intake (agents/voice_intake.py).

Browser -> server (JSON): first {"token": "<Firebase ID token>"}, then any of
  {"audio": "<base64 PCM16 mono 16 kHz>"}, {"text": "typed reply"}, {"end": true}
Server -> browser (JSON):
  {"audio": "<base64 PCM16 mono 24 kHz>"}, {"transcript": {"who": "ai"|"you", "text": "..."}},
  {"turn_complete": true}, {"saved": {"document": Document}} or {"saved": null} (too little
  said to keep), {"error": "..."}
"""

import asyncio
import base64
import contextlib
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from google.genai import types

from ..agents import hearing, voice_intake
from ..auth import verify_token
from ..config import get_settings
from ..models import Case, CaseEvent, CaseStatus, DocType, Document
from ..tools import files, store
from .documents import MAX_DOCUMENTS

log = logging.getLogger(__name__)
router = APIRouter(tags=["voice intake"])
BUSY = (
    "The voice service is busy right now. Please try again in a few minutes, or type what happened."
)
SESSION_SECONDS = 10 * 60


class _Talk:
    def __init__(self) -> None:
        self.lines: list[tuple[str, str]] = []  # (who, text), consecutive chunks merged
        self.end_requested = False
        self.ai_spoke = False

    def add(self, who: str, text: str) -> None:
        if self.lines and self.lines[-1][0] == who:
            self.lines[-1] = (who, self.lines[-1][1] + text)
        else:
            self.lines.append((who, text))


def _text(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])


async def _from_browser(ws: WebSocket, session, talk: _Talk) -> None:
    while True:
        msg = await ws.receive_json()
        if "audio" in msg:
            await session.send_realtime_input(
                audio=types.Blob(
                    data=base64.b64decode(msg["audio"]), mime_type="audio/pcm;rate=16000"
                )
            )
        elif "text" in msg:
            talk.add("you", " " + msg["text"])
            await session.send_client_content(turns=_text(msg["text"]), turn_complete=True)
        elif msg.get("end"):
            talk.end_requested = True
            talk.ai_spoke = False
            await session.send_client_content(
                turns=_text(
                    "[the person is done: repeat back what you understood, then call finish]"
                ),
                turn_complete=True,
            )


async def _from_gemini(ws: WebSocket, session, talk: _Talk) -> None:
    while True:
        async for msg in session.receive():
            if msg.data:
                await ws.send_json({"audio": base64.b64encode(msg.data).decode()})
            content = msg.server_content
            if content and content.input_transcription and content.input_transcription.text:
                talk.add("you", content.input_transcription.text)
                await ws.send_json(
                    {"transcript": {"who": "you", "text": content.input_transcription.text}}
                )
            if content and content.output_transcription and content.output_transcription.text:
                talk.ai_spoke = True
                talk.add("ai", content.output_transcription.text)
                await ws.send_json(
                    {"transcript": {"who": "ai", "text": content.output_transcription.text}}
                )
            if content and content.turn_complete:
                if talk.end_requested and talk.ai_spoke:
                    return  # it said its summary after "done"; don't rely on it calling `finish`
                await ws.send_json({"turn_complete": True})
            if msg.tool_call and any(c.name == "finish" for c in msg.tool_call.function_calls):
                return


def _authorise(first: dict, case_id: str) -> Case:
    uid = verify_token(first.get("token"), get_settings())
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    if case.status != CaseStatus.COLLECTING:
        raise HTTPException(409, "This case is already being analysed.")
    if case.documents_deleted_at or len(case.documents) >= MAX_DOCUMENTS:
        raise HTTPException(409, "This case can't take more documents.")
    return case


def _save(case_id: str, talk: _Talk) -> Document | None:
    case = store.load_case(case_id)
    if not case or voice_intake.patient_words(talk.lines) < voice_intake.MIN_WORDS:
        return None
    now = datetime.now(UTC)
    name = f"spoken-account-{now:%Y%m%d-%H%M}.txt"
    doc_id = uuid.uuid4().hex
    text = voice_intake.transcript(talk.lines, case, now)
    uri = files.put(f"{case.id}/{doc_id}-{name}", text.encode("utf-8"), "text/plain")
    doc = Document(id=doc_id, filename=name, gcs_uri=uri, doc_type=DocType.OTHER, uploaded_at=now)
    case.documents.append(doc)
    case.events.append(
        CaseEvent(
            at=now,
            kind="voice_intake",
            text="You told us what happened by voice. It is saved in your files.",
        )
    )
    store.save_case(case)
    return doc


@router.websocket("/cases/{case_id}/voice-intake")
async def voice_intake_socket(ws: WebSocket, case_id: str) -> None:
    await ws.accept()
    try:
        case = _authorise(await asyncio.wait_for(ws.receive_json(), timeout=15), case_id)
    except (HTTPException, TimeoutError) as exc:
        await ws.send_json({"error": getattr(exc, "detail", "Send the login token first.")})
        await ws.close(code=4401)
        return

    talk = _Talk()
    try:
        async with hearing.client().aio.live.connect(
            model=get_settings().live_model, config=voice_intake.live_config(case)
        ) as session:
            await session.send_client_content(
                turns=_text("[the person has joined: greet them]"), turn_complete=True
            )
            upstream = asyncio.create_task(_from_browser(ws, session, talk))
            try:
                await asyncio.wait_for(_from_gemini(ws, session, talk), SESSION_SECONDS)
            except (WebSocketDisconnect, TimeoutError):
                pass
            finally:
                upstream.cancel()
                with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect):
                    await upstream
    except Exception:
        # Quota (1011 "Resource exhausted") or a dropped Live session: tell the patient instead
        # of leaving them on "Connecting…", and still keep whatever they already said.
        log.exception("voice intake: Live session failed")
        with contextlib.suppress(RuntimeError, WebSocketDisconnect):
            await ws.send_json({"error": BUSY})

    # Saved even if the browser left early: whatever the patient said is theirs to keep.
    doc = await asyncio.to_thread(_save, case_id, talk)
    with contextlib.suppress(RuntimeError, WebSocketDisconnect):
        await ws.send_json({"saved": {"document": doc.model_dump(mode="json")} if doc else None})
        await ws.close()
