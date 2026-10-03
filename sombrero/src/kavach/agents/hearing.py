"""Hearing rehearsal with the Gemini Live API.

Gemini plays the dispute body (e.g. the Insurance Ombudsman or a FIDReC mediator) and the
insurer's representative, using the patient's real case. After each answer the server
coaches it with a text model (the Live model role-plays only: it proved unreliable at
judging answers mid-conversation), and the UI shows that as text.
"""

import json

from google import genai
from google.genai import types
from pydantic import BaseModel

from ..config import get_settings
from ..models import Case
from ..tools import packs
from . import llm

LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "zh": "Mandarin Chinese",
    "ms": "Malay",
}
MAX_QUESTIONS = 5
KEY_FACTS = (
    "insurer",
    "policy_start",
    "admission_date",
    "first_diagnosis_date",
    "diagnosis",
    "claim_amount",
    "amount_approved",
    "rejection_reason",
    "cited_clause",
    "rejection_date",
)


class Coaching(BaseModel):
    score: int  # 1 (weak) to 5 (excellent)
    feedback: str
    better_answer: str


COACH_PROMPT = """You coach a patient rehearsing a health-insurance dispute hearing. You get the
question just asked (by the dispute body or the insurer's representative), the patient's exact
answer, and the patient's verified arguments with their sources.
Judge only the answer actually given. score: 1-5 (5 = answers the question directly, cites the
right evidence or clause, stays calm and concise). feedback: one or two plain sentences on what
worked and what was missing. better_answer: a stronger first-person answer to the same question,
using only the case facts and verified arguments (no invented facts)."""


def coach(case: Case, question: str, answer: str) -> Coaching:
    context = {
        "question": question,
        "answer": answer,
        "facts": case.facts.model_dump(mode="json", exclude_none=True) if case.facts else {},
        "arguments": _arguments(case),
        "language": LANGUAGES.get(case.language, "English"),
    }
    return llm.structured(COACH_PROMPT, [], Coaching, context=context)


FINISH = types.FunctionDeclaration(
    name="finish",
    description="End the rehearsal after the closing statement.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "summary": types.Schema(
                type=types.Type.STRING, description="How the patient did overall, in two sentences."
            ),
            "top_tips": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING),
                description="Three short tips for the real hearing.",
            ),
        },
        required=["summary", "top_tips"],
    ),
)


def _dispute_body(case: Case) -> str:
    return packs.load(case.country)["dispute_process"][-1]["step"]


def _arguments(case: Case) -> list[dict]:
    return [
        {"claim": a.claim, "sources": [f"{s.ref}: {s.quote}" for s in a.sources]}
        for a in (case.assessment.arguments if case.assessment else [])
    ]


def instructions(case: Case) -> str:
    known = case.facts.model_dump(mode="json") if case.facts else {}
    # Spell out gaps: given only the known facts, the Live model invented e.g. a policy start date.
    facts = {k: (known.get(k) if known.get(k) is not None else "unknown") for k in KEY_FACTS}
    facts.update({k: v for k, v in known.items() if v is not None})
    arguments = _arguments(case)
    body = _dispute_body(case)
    language = LANGUAGES.get(case.language, "English")
    return f"""You run a practice hearing so a patient can rehearse their health-insurance dispute
before the real {body}. Speak {language}. Keep every turn short (under 40 seconds).

You voice BOTH roles yourself; the patient is the only other person present:
- "{body}": neutral and courteous; opens the hearing, asks the patient focused questions, keeps time.
- "Insurer's representative": politely but firmly defends the rejection using the insurer's
  stated grounds below, and challenges weak points in the patient's answers.
Announce the speaker before each part, e.g. "Insurer's representative: ...". Never hand over
to the representative and wait: if the representative should speak, say their words yourself
in the same turn. EVERY turn must end with exactly one question addressed to the patient.

Flow: the {body} opens and asks the patient to state their complaint. Then ask up to
{MAX_QUESTIONS} questions, alternating which role asks, each probing a different issue (the
insurer's ground, dates and documents, the specific clause, what relief is sought). After at
least three of the patient's answers, the {body} invites a short closing statement; after the
closing statement, thank the patient and call `finish`. If the patient asks to stop, call
`finish` at once. Never call `finish` before the patient has answered.
Messages in square brackets, like [session started], are cues from the app, not the patient.

Facts marked "unknown" are unknown to everyone, including the insurer. Never state or assume
a value for them (no invented dates, amounts or records); either role may ASK the patient about
them instead.

Stay realistic and fair: never invent facts beyond the case below, never promise an outcome,
and never give legal advice outside the role-play.

CASE FACTS: {json.dumps(facts, ensure_ascii=False)}
PATIENT'S VERIFIED ARGUMENTS: {json.dumps(arguments, ensure_ascii=False)}"""


def live_config(case: Case) -> types.LiveConnectConfig:
    s = get_settings()
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=instructions(case),
        tools=[types.Tool(function_declarations=[FINISH])],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=s.live_voice)
            )
        ),
    )


def client() -> genai.Client:
    s = get_settings()
    return genai.Client(vertexai=True, project=s.gcp_project, location=s.live_location)


class Debrief(BaseModel):
    summary: str
    top_tips: list[str]


DEBRIEF_PROMPT = """You debrief a patient after a practice hearing for their health-insurance dispute.
You get each question, the patient's answer and the coach's score and feedback. Write
summary: two plain sentences on how they did overall; top_tips: three short, specific tips for
the real hearing, based on their weakest answers. Use only what is given."""


def debrief(case: Case, coaching: list[dict]) -> Debrief:
    context = {"coaching": coaching, "language": LANGUAGES.get(case.language, "English")}
    return llm.structured(DEBRIEF_PROMPT, [], Debrief, context=context)
