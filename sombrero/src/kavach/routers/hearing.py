"""WebSocket relay between the browser and a Gemini Live hearing rehearsal.

Browser -> server (JSON): first {"token": "<Firebase ID token>"}, then any of
  {"audio": "<base64 PCM16 mono 16 kHz>"}, {"text": "typed answer"}, {"end": true}
Server -> browser (JSON):
  {"audio": "<base64 PCM16 mono 24 kHz>"}, {"transcript": {"who": "ai"|"you", "text": "..."}},
  {"turn_complete": true}, {"coach": {"question", "answer", "score", "feedback", "better_answer"}},
  {"done": {"summary", "top_tips", "average_score"}}, {"error": "..."}
"""

import asyncio
import base64
import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from google.genai import types

from ..agents import hearing
from ..auth import verify_token
from ..config import get_settings
from ..models import Case, CaseEvent
from ..tools import store

router = APIRouter(tags=["hearing"])
MIN_ANSWERS = 3  # the Live model sometimes calls `finish` before the hearing has happened


@dataclass
class _Turns:
    """Pairs each question the AI asked with the patient's answer, for coaching."""

    question: str = ""
    speaking: str = ""
    answer: str = ""
    answers: int = 0
    stop_requested: bool = False
    scores: list[int] = field(default_factory=list)
    coaching: list[dict] = field(default_factory=list)
    tasks: set = field(default_factory=set)


async def _coach(ws: WebSocket, case: Case, turns: _Turns, question: str, answer: str) -> None:
    result = await asyncio.to_thread(hearing.coach, case, question, answer)
    turns.scores.append(result.score)
    turns.coaching.append({"question": question, "answer": answer, **result.model_dump()})
    with contextlib.suppress(RuntimeError, WebSocketDisconnect):
        await ws.send_json(
            {"coach": {"question": question, "answer": answer, **result.model_dump()}}
        )


def _text(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])


async def _from_browser(ws: WebSocket, session, turns: _Turns) -> None:
    while True:
        msg = await ws.receive_json()
        if "audio" in msg:
            await session.send_realtime_input(
                audio=types.Blob(
                    data=base64.b64decode(msg["audio"]), mime_type="audio/pcm;rate=16000"
                )
            )
        elif "text" in msg:
            turns.answer += " " + msg["text"]
            await session.send_client_content(turns=_text(msg["text"]), turn_complete=True)
        elif msg.get("end"):
            turns.stop_requested = True
            await session.send_client_content(
                turns=_text("[the patient asked to stop: end the rehearsal now]"),
                turn_complete=True,
            )


async def _from_gemini(ws: WebSocket, session, case: Case, turns: _Turns) -> dict:
    while True:
        async for msg in session.receive():
            if msg.data:
                await ws.send_json({"audio": base64.b64encode(msg.data).decode()})
            content = msg.server_content
            if content and content.input_transcription and content.input_transcription.text:
                turns.answer += content.input_transcription.text
                await ws.send_json(
                    {"transcript": {"who": "you", "text": content.input_transcription.text}}
                )
            if content and content.output_transcription and content.output_transcription.text:
                if turns.answer.strip() and turns.question:
                    # The AI started its next turn, so the patient's answer is complete.
                    turns.answers += 1
                    task = asyncio.create_task(
                        _coach(ws, case, turns, turns.question, turns.answer.strip())
                    )
                    turns.tasks.add(task)
                    task.add_done_callback(turns.tasks.discard)
                turns.answer = ""
                turns.speaking += content.output_transcription.text
                await ws.send_json(
                    {"transcript": {"who": "ai", "text": content.output_transcription.text}}
                )
            if content and content.turn_complete:
                if turns.stop_requested and turns.speaking.strip():
                    return {}  # Gemini said goodbye; don't rely on it calling `finish`
                if turns.speaking.strip():
                    turns.question, turns.speaking = turns.speaking.strip(), ""
                await ws.send_json({"turn_complete": True})  # UI: "your turn"
            if msg.tool_call:
                calls = msg.tool_call.function_calls
                finish = next((c for c in calls if c.name == "finish"), None)
                if finish and (turns.answers >= MIN_ANSWERS or turns.stop_requested):
                    return dict(finish.args or {})
                too_early = (
                    f"Too early: the patient has answered {turns.answers} questions. "
                    "Continue the hearing and ask the patient the next question."
                )
                await session.send_tool_response(
                    function_responses=[
                        types.FunctionResponse(id=c.id, name=c.name, response={"error": too_early})
                        for c in calls
                    ]
                )


def _authorise(first: dict, case_id: str) -> Case:
    uid = verify_token(first.get("token"), get_settings())
    case = store.load_case(case_id)
    if not case or case.owner != uid:
        raise HTTPException(404, "Case not found.")
    if not case.assessment:
        raise HTTPException(409, "Run the analysis first.")
    return case


@router.websocket("/cases/{case_id}/hearing")
async def hearing_socket(ws: WebSocket, case_id: str) -> None:
    await ws.accept()
    try:
        case = _authorise(await asyncio.wait_for(ws.receive_json(), timeout=15), case_id)
    except (HTTPException, TimeoutError) as exc:
        await ws.send_json({"error": getattr(exc, "detail", "Send the login token first.")})
        await ws.close(code=4401)
        return

    s = get_settings()
    turns = _Turns()
    result = None
    async with hearing.client().aio.live.connect(
        model=s.live_model, config=hearing.live_config(case)
    ) as session:
        await session.send_client_content(
            turns=_text("[session started: open the hearing]"), turn_complete=True
        )
        upstream = asyncio.create_task(_from_browser(ws, session, turns))
        try:
            result = await _from_gemini(ws, session, case, turns)
        except WebSocketDisconnect:
            pass
        finally:
            upstream.cancel()
            with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect):
                await upstream

    if result is not None:
        if turns.answer.strip() and turns.question:  # the closing statement
            await _coach(ws, case, turns, turns.question, turns.answer.strip())
        await asyncio.gather(*turns.tasks, return_exceptions=True)
        if turns.coaching:
            # Debrief from what was actually said, not the Live model's own recollection.
            report = await asyncio.to_thread(hearing.debrief, case, turns.coaching)
            result = {"summary": report.summary, "top_tips": report.top_tips}
        tips = result.get("top_tips") or []
        tips = [tips] if isinstance(tips, str) else list(tips)
        average = round(sum(turns.scores) / len(turns.scores), 1) if turns.scores else None
        done = {"summary": result.get("summary", ""), "top_tips": tips, "average_score": average}
        with contextlib.suppress(RuntimeError, WebSocketDisconnect):
            await ws.send_json({"done": done})
        case = store.load_case(case_id) or case
        case.events.append(
            CaseEvent(
                at=datetime.now(UTC),
                kind="rehearsal",
                text=f"Hearing rehearsal: average score {average}/5. {done['summary']} Tips: {'; '.join(tips)}",
            )
        )
        store.save_case(case)
    with contextlib.suppress(RuntimeError):
        await ws.close()
