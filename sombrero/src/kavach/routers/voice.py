"""Phone line over Twilio.

Call flow (each step is a Twilio webhook answered with TwiML):
  POST /voice/incoming  find the caller's Kavach account by phone number and their latest case,
                        then ask for the last 4 digits of the policy (or claim) number
  POST /voice/verify    check the digits (3 tries), then offer: 1 case status, 2 rehearse hearing
  POST /voice/menu      connect a bidirectional media stream to WS /voice/stream
  WS   /voice/stream    Twilio audio (8 kHz mu-law) <-> Gemini Live (16 kHz in, 24 kHz out)

Webhooks must carry a valid X-Twilio-Signature. The stream's parameters (case, mode) are
HMAC-signed by us, so nobody can open a stream for someone else's case.
"""

import asyncio
import base64
import contextlib
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from urllib.parse import urlencode
from xml.sax.saxutils import escape, quoteattr

from fastapi import APIRouter, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from google.genai import types

from ..agents import hearing, voice
from ..config import get_settings
from ..models import Case, CaseEvent
from ..tools import audio, store

router = APIRouter(prefix="/voice", tags=["voice"])
VOICE = "Polly.Joanna"  # Twilio's TTS for the short menu prompts before Gemini takes over
STREAM_TTL = 300  # seconds a signed stream link stays valid
MAX_CALL = 15 * 60


# ── Twilio request signing ────────────────────────────────────────────────────────────


def twilio_signature(token: str, url: str, params: dict[str, str]) -> str:
    """Twilio's scheme: base64(HMAC-SHA1(token, url + each sorted key + value))."""
    data = url + "".join(k + params[k] for k in sorted(params))
    return base64.b64encode(hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()).decode()


def _public_url(request: Request) -> str:
    """The URL Twilio called (Cloud Run terminates TLS, so rebuild it as https)."""
    base = get_settings().public_url.rstrip("/") or f"https://{request.headers.get('host')}"
    query = f"?{request.url.query}" if request.url.query else ""
    return f"{base}{request.url.path}{query}"


async def _twilio_form(request: Request) -> dict[str, str]:
    s = get_settings()
    form = {k: str(v) for k, v in (await request.form()).items()}
    if s.auth_disabled and not s.twilio_auth_token:
        return form  # local testing without Twilio
    expected = twilio_signature(s.twilio_auth_token, _public_url(request), form)
    if not hmac.compare_digest(expected, request.headers.get("X-Twilio-Signature", "")):
        raise HTTPException(403, "Bad Twilio signature.")
    return form


def _sign(*parts: str) -> str:
    key = get_settings().twilio_auth_token.encode() or b"dev"
    return hmac.new(key, "|".join(parts).encode(), hashlib.sha256).hexdigest()


# ── TwiML helpers ─────────────────────────────────────────────────────────────────────


def _twiml(body: str) -> Response:
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>'
    return Response(xml, media_type="application/xml")


def _say(text: str) -> str:
    return f"<Say voice={quoteattr(VOICE)}>{escape(text)}</Say>"


def _gather(action: str, prompt: str, digits: int) -> str:
    return (
        f"<Gather input={quoteattr('dtmf')} numDigits={quoteattr(str(digits))} "
        f"action={quoteattr(action)} method={quoteattr('POST')} timeout={quoteattr('8')}>"
        f"{_say(prompt)}</Gather>"
    )


def _action(path: str, **params: str) -> str:
    return f"{path}?{urlencode(params)}" if params else path


# ── Who is calling ────────────────────────────────────────────────────────────────────


def _uid_for_phone(phone: str) -> str | None:
    if get_settings().auth_disabled:
        return "dev-user"
    from firebase_admin import auth, get_app, initialize_app

    try:
        get_app()
    except ValueError:
        initialize_app()
    try:
        return auth.get_user_by_phone_number(phone).uid
    except (auth.UserNotFoundError, ValueError):  # ValueError: not an E.164 number
        return None


def _latest_case(uid: str) -> Case | None:
    """Newest case that has results to talk about."""
    return next((c for c in store.list_cases(uid) if c.assessment or c.discharge_check), None)


def _pin(case: Case) -> str | None:
    """Last 4 digits of the policy number, else the claim number."""
    for value in (case.facts.policy_number, case.facts.claim_number) if case.facts else ():
        digits = "".join(ch for ch in value or "" if ch.isdigit())
        if len(digits) >= 4:
            return digits[-4:]
    return None


def _menu(case: Case) -> str:
    sig = _sign("menu", case.id)
    rehearse = " Press 2 to practise your hearing." if case.assessment else ""
    return _gather(
        _action("/voice/menu", case=case.id, sig=sig),
        f"Press 1 to hear where your case stands and what to do next.{rehearse}",
        1,
    )


@router.post("/incoming")
async def incoming(request: Request) -> Response:
    form = await _twilio_form(request)
    uid = _uid_for_phone(form.get("From", ""))
    case = _latest_case(uid) if uid else None
    if not case:
        return _twiml(
            _say(
                "Welcome to Kavach. We couldn't find a case for this phone number. "
                "Please sign in to the Kavach app with this number and upload your documents "
                "first. Goodbye."
            )
            + "<Hangup/>"
        )
    pin = _pin(case)
    if not pin:
        return _twiml(_say("Welcome to Kavach.") + _menu(case))
    action = _action("/voice/verify", case=case.id, tries="0", sig=_sign("verify", case.id))
    return _twiml(
        _say("Welcome to Kavach.")
        + _gather(action, "For your security, enter the last four digits of your policy number.", 4)
        + _say("We didn't get that. Goodbye.")
    )


@router.post("/verify")
async def verify(request: Request, case: str, tries: int, sig: str) -> Response:
    form = await _twilio_form(request)
    if not hmac.compare_digest(sig, _sign("verify", case)):
        raise HTTPException(403, "Bad link.")
    kase = store.load_case(case)
    if not kase or _pin(kase) != form.get("Digits"):
        if tries >= 2:
            return _twiml(_say("Those digits don't match our records. Goodbye.") + "<Hangup/>")
        action = _action("/voice/verify", case=case, tries=str(tries + 1), sig=sig)
        return _twiml(_gather(action, "Those digits don't match. Please try again.", 4))
    return _twiml(_menu(kase) + _say("We didn't get that. Goodbye."))


@router.post("/menu")
async def menu(request: Request, case: str, sig: str) -> Response:
    form = await _twilio_form(request)
    if not hmac.compare_digest(sig, _sign("menu", case)):
        raise HTTPException(403, "Bad link.")
    mode = "rehearse" if form.get("Digits") == "2" else "status"
    ts = str(int(time.time()))
    host = (get_settings().public_url or f"https://{request.headers.get('host')}").split("://")[-1]
    params = {"case": case, "mode": mode, "ts": ts, "sig": _sign("stream", case, mode, ts)}
    tags = "".join(
        f"<Parameter name={quoteattr(k)} value={quoteattr(v)}/>" for k, v in params.items()
    )
    intro = "Connecting you now." if mode == "status" else "Starting your practice hearing."
    return _twiml(
        _say(intro) + f"<Connect><Stream url={quoteattr(f'wss://{host}/voice/stream')}>{tags}"
        "</Stream></Connect>"
    )


# ── Media stream ──────────────────────────────────────────────────────────────────────


def _authorise_stream(params: dict) -> tuple[Case, str]:
    case_id, mode, ts = params.get("case", ""), params.get("mode", ""), params.get("ts", "0")
    good = hmac.compare_digest(params.get("sig", ""), _sign("stream", case_id, mode, ts))
    if not good or abs(time.time() - int(ts)) > STREAM_TTL or mode not in ("status", "rehearse"):
        raise HTTPException(403, "Bad stream link.")
    case = store.load_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found.")
    return case, mode


async def _from_twilio(ws: WebSocket, session, call: dict) -> None:
    while True:
        msg = json.loads(await ws.receive_text())
        if msg.get("event") == "media":
            pcm = audio.phone_to_live(base64.b64decode(msg["media"]["payload"]))
            await session.send_realtime_input(
                audio=types.Blob(data=pcm, mime_type="audio/pcm;rate=16000")
            )
        elif msg.get("event") == "stop":
            call["ended"] = True
            return


async def _to_twilio(ws: WebSocket, session, sid: str, call: dict) -> None:
    rest = b""  # Live chunks need not be a multiple of 3 samples; carry the remainder
    ending = False  # the model asked to hang up
    interrupted = False  # the caller talked over the current turn
    spoke = False  # audio was sent in the current turn
    silent_turns = 0  # turns since hang-up was requested that played nothing
    while True:
        async for msg in session.receive():
            if msg.data:
                spoke = True
                pcm = rest + msg.data
                usable = len(pcm) // 6 * 6
                pcm, rest = pcm[:usable], pcm[usable:]
                payload = base64.b64encode(audio.live_to_phone(pcm)).decode()
                await ws.send_json(
                    {"event": "media", "streamSid": sid, "media": {"payload": payload}}
                )
            content = msg.server_content
            if content and content.interrupted:
                rest, interrupted = b"", True
                await ws.send_json({"event": "clear", "streamSid": sid})  # caller talked over us
            if content and content.input_transcription and content.input_transcription.text:
                call["transcript"].append(("caller", content.input_transcription.text))
            if content and content.output_transcription and content.output_transcription.text:
                call["transcript"].append(("kavach", content.output_transcription.text))
            if content and content.turn_complete:
                # End after a goodbye turn that played in full; an interrupted one may have
                # been cut to a syllable, so keep listening instead.
                if ending and not interrupted and (spoke or silent_turns >= 3):
                    await asyncio.sleep(1.5)  # Twilio plays what we sent; let it finish
                    return
                if ending and not spoke:
                    silent_turns += 1
                if ending and silent_turns == 1:
                    # It hung up silently; one nudge so the caller hears a goodbye.
                    await session.send_client_content(
                        turns=types.Content(
                            role="user", parts=[types.Part(text="[say a short goodbye now]")]
                        ),
                        turn_complete=True,
                    )
                interrupted = spoke = False
            if msg.tool_call:
                calls = msg.tool_call.function_calls
                # Native-audio models may call the tool before speaking the goodbye, so answer
                # it and end only when that turn completes.
                ending = ending or any(c.name in ("hang_up", "finish") for c in calls)
                await session.send_tool_response(
                    function_responses=[
                        types.FunctionResponse(id=c.id, name=c.name, response={"ok": True})
                        for c in calls
                    ]
                )


def _log_call(case_id: str, mode: str, started: float) -> None:
    case = store.load_case(case_id)
    if not case:
        return
    minutes = max(1, round((time.time() - started) / 60))
    what = "practised the hearing" if mode == "rehearse" else "asked about the case"
    case.events.append(
        CaseEvent(at=datetime.now(UTC), kind="call", text=f"Phone call: {what} (~{minutes} min).")
    )
    store.save_case(case)


@router.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    await ws.accept()
    try:
        sid, params = "", {}
        while not sid:  # "connected" comes first, then "start" with our parameters
            msg = json.loads(await asyncio.wait_for(ws.receive_text(), timeout=10))
            if msg.get("event") == "start":
                sid = msg["start"]["streamSid"]
                params = msg["start"].get("customParameters", {})
        case, mode = _authorise_stream(params)
    except (HTTPException, TimeoutError, KeyError, ValueError, WebSocketDisconnect):
        with contextlib.suppress(RuntimeError):
            await ws.close(code=4403)
        return

    started = time.time()
    call: dict = {"transcript": [], "ended": False}
    cue = (
        "[call connected: greet the caller]"
        if mode == "status"
        else "[session started: open the hearing]"
    )
    async with hearing.client().aio.live.connect(
        model=get_settings().live_model, config=voice.live_config(case, mode)
    ) as session:
        await session.send_client_content(
            turns=types.Content(role="user", parts=[types.Part(text=cue)]), turn_complete=True
        )
        upstream = asyncio.create_task(_from_twilio(ws, session, call))
        downstream = asyncio.create_task(_to_twilio(ws, session, sid, call))
        with contextlib.suppress(WebSocketDisconnect, TimeoutError):
            await asyncio.wait_for(
                asyncio.wait({upstream, downstream}, return_when=asyncio.FIRST_COMPLETED),
                timeout=MAX_CALL,
            )
        for task in (upstream, downstream):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
                await task
    _log_call(case.id, mode, started)
    with contextlib.suppress(RuntimeError):
        await ws.close()
