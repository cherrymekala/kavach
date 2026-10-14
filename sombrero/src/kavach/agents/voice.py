"""Phone line: a caller hears their case status and next step, or rehearses their hearing.

The same Gemini Live model as the web rehearsal, fed by Twilio's phone audio. Like the
rehearsal, the Live model (us-central1) never sees who the patient is: no name, policy,
claim number or hospital.
"""

import json

from google.genai import types

from ..config import get_settings
from ..models import Case
from ..tools import packs
from . import hearing

HANG_UP = types.FunctionDeclaration(
    name="hang_up",
    description="End the phone call after saying goodbye, when the caller has no more questions.",
)


def _status(case: Case) -> dict:
    """What the caller may ask about, minus anything identifying."""
    steps = packs.load(case.country)["dispute_process"]
    step = steps[min(case.escalation_step, len(steps) - 1)]
    facts = case.facts.model_dump(mode="json", exclude_none=True) if case.facts else {}
    a, d = case.assessment, case.discharge_check
    return {
        "kind": case.kind,
        "status": case.status,
        "facts": {k: v for k, v in facts.items() if k not in hearing.IDENTIFYING},
        "chances": a.strength if a else None,
        "arguments": [x.claim for x in a.arguments] if a else [],
        "missing_documents": a.missing_documents if a else [],
        "discharge_check": (
            {"verdict": d.verdict, "risks": [f"{r.title} Fix: {r.fix}" for r in d.risks]}
            if d
            else None
        ),
        "dispute_steps": [s["step"] for s in steps],
        "current_step": step["step"],
        "reply_deadline": case.next_deadline.date().isoformat() if case.next_deadline else None,
        "recent_events": [f"{e.at:%d %b %Y}: {e.text}" for e in case.events[-5:]],
        "amount_recovered": case.amount_recovered,
    }


def status_instructions(case: Case) -> str:
    language = hearing.LANGUAGES.get(case.language, "English")
    return f"""You are Kavach, answering a phone call from a patient about their health-insurance
claim. Greet them in {language}. After that, ALWAYS reply in the language the caller last spoke
(if they ask in English, answer in English). Speak warmly and plainly, in short turns (this is a phone call: one or two
sentences, then let them speak). Never use jargon without explaining it.

Start by saying you have their case open, then in one sentence tell them where it stands and the
single most important next step, and ask what they would like to know.
You can explain: why the claim was rejected and what that means; their chances and the main
arguments; which documents would help; the dispute steps and the current one; deadlines; and, for
a discharge check, what to fix before leaving hospital.
Use only the case data below. If something is not in it, say you don't have that and suggest
they check the Kavach app. Never give legal advice beyond the case data, never invent dates or
amounts, and never read out policy, claim or ID numbers. To change anything (upload documents,
mark a letter as sent), tell them to use the Kavach app.
When the caller says goodbye or has no more questions, first say a short goodbye out loud,
then call `hang_up`.

CASE: {json.dumps(_status(case), ensure_ascii=False, default=str)}"""


def live_config(case: Case, mode: str) -> types.LiveConnectConfig:
    s = get_settings()
    if mode == "rehearse":
        system, tools = hearing.instructions(case), [hearing.FINISH, HANG_UP]
    else:
        system, tools = status_instructions(case), [HANG_UP]
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=system,
        tools=[types.Tool(function_declarations=tools)],
        input_audio_transcription=types.AudioTranscriptionConfig(
            language_codes=hearing.speech_languages(case)
        ),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=s.live_voice)
            )
        ),
    )
