"""Voice-first intake: the patient tells what happened, in their language, through Gemini Live.

For people who find forms hard. A short, warm interview; the transcript becomes a document in
the case, so the normal analysis reads it alongside any uploads. The Live model runs in
us-central1, so it never asks for names, phone numbers, addresses or policy and claim numbers:
the uploaded papers carry those.
"""

from datetime import datetime

from google.genai import types

from ..config import get_settings
from ..models import Case
from . import hearing

MAX_QUESTIONS = 7
MIN_WORDS = 8  # less than this from the patient is not worth saving as their account

FINISH = types.FunctionDeclaration(
    name="finish",
    description="End the conversation once you have repeated back what you understood.",
    parameters=types.Schema(type=types.Type.OBJECT, properties={}),
)

# Keyed by CaseKind value (a str enum), so "preauth" works whether or not that kind exists here.
TOPICS: dict[str, tuple[str, str]] = {
    "dispute": (
        "their health-insurance claim was rejected or cut",
        (
            "the illness or treatment; when they were admitted and discharged; what the insurer "
            "said and when; the reason the insurer gave, in its words if they remember; the amount "
            "claimed and the amount paid; roughly when the policy started; which papers they have "
            "(rejection letter, policy, discharge summary, bills)"
        ),
    ),
    "preauth": (
        (
            "the hospital's cashless (pre-authorisation) request was refused or queried while "
            "they are in hospital"
        ),
        (
            "the illness and the planned treatment; when they were admitted; what the insurer or "
            "TPA said and when; the reason given; the amount asked; roughly when the policy "
            "started; which papers they have (the refusal message, policy, doctor's notes)"
        ),
    ),
    "pre_discharge": (
        "they are about to be discharged and want to check the claim before it is filed",
        (
            "the illness and treatment; when they were admitted; the room they are in and its "
            "daily rent; any known conditions before the policy; roughly when the policy "
            "started; which papers they have (policy, discharge summary, interim bill)"
        ),
    ),
}


def instructions(case: Case) -> str:
    language = hearing.LANGUAGES.get(case.language, "English")
    situation, ask_about = TOPICS.get(str(case.kind), TOPICS["dispute"])
    return f"""You are Kavach, a calm, kind helper. The person speaking to you {situation}.
Help them tell what happened, by voice, so Kavach can prepare their case.

Speak {language}; if they switch language, follow them. Keep each turn to one or two short
sentences and ask ONE question at a time. Start by greeting them in one sentence and asking
them to tell you what happened, in their own words.

Then ask only about what they have not already said, at most {MAX_QUESTIONS} questions in all:
{ask_about}. If they are upset, acknowledge it in a few words and carry on gently.

Never ask for names, phone numbers, addresses, or policy, claim or ID numbers: their papers will
give those. If they say them anyway, do not repeat them. Do not give legal advice, do not judge
their chances and never promise an outcome.

When you have enough, or they say they are done, repeat back in two sentences what you
understood, tell them it is saved with their case and that they can add photos of their papers
next, then call `finish`."""


def live_config(case: Case) -> types.LiveConnectConfig:
    s = get_settings()
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=instructions(case),
        tools=[types.Tool(function_declarations=[FINISH])],
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


def transcript(lines: list[tuple[str, str]], case: Case, when: datetime) -> str:
    """The saved account: who said what, marked as an automatic transcript."""
    language = hearing.LANGUAGES.get(case.language, "English")
    head = (
        f"Patient's account, told by voice to Kavach on {when:%d %b %Y %H:%M} UTC ({language}).\n"
        "Transcribed automatically from speech; names and numbers may be misheard.\n\n"
    )
    body = "\n".join(
        f"{'Patient' if who == 'you' else 'Kavach'}: {text.strip()}"
        for who, text in lines
        if text.strip()
    )
    return head + body + "\n"


def patient_words(lines: list[tuple[str, str]]) -> int:
    return sum(len(text.split()) for who, text in lines if who == "you")
