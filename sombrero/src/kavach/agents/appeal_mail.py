"""The appeal email: a short cover note around the letter, and a quick read of the reply."""

import logging
import re

from pydantic import BaseModel

from ..config import get_settings
from ..models import Case
from . import llm

log = logging.getLogger(__name__)

# Letter placeholders the patient still has to fill in, e.g. "[Your Address]".
BLANK = re.compile(r"\[[^\]\n]{2,60}\]")


def blanks(text: str) -> list[str]:
    return sorted(set(BLANK.findall(text or "")))


def compose(case: Case, reply_to: str | None) -> tuple[str, str]:
    """Subject and plain-text body. The letter itself is the body; the PDF is attached."""
    letter = case.letter
    name = (case.complainant.name if case.complainant else None) or "the policyholder"
    replies = (
        "Please reply to this email. Your reply reaches me directly."
        if reply_to
        else "Please reply to this email."
    )
    body = (
        "Dear Grievance Redressal Officer,\n\n"
        "Please find my appeal against the rejection of my health insurance claim below, "
        f"also attached as a PDF. {replies}\n\n"
        f"{letter.english.strip()}\n\n"
        f"— {name}\n(sent with Kavach on my behalf)"
    )
    return letter.subject, body


class ReplyRead(BaseModel):
    outcome: str  # paid | partly_paid | rejected | needs_documents | acknowledged | other
    summary: str  # one plain-English sentence for the patient


READ_PROMPT = """An insurer replied by email to a patient's appeal against a rejected health claim.
Classify the reply: paid (they will pay in full), partly_paid, rejected (rejection upheld),
needs_documents (they ask for papers or information), acknowledged (received, under review),
other. Then write ONE short, plain sentence telling the patient what the insurer said.
Do not give advice and do not invent anything that is not in the email."""


def read_reply(subject: str, text: str) -> ReplyRead | None:
    """Best effort: None when the model is unavailable (the reply is still logged)."""
    try:
        return llm.structured(
            READ_PROMPT,
            [],
            ReplyRead,
            context={"subject": subject, "body": text[:6000]},
            model=get_settings().model_fast,
        )
    except Exception:
        log.warning("reading the insurer's reply failed", exc_info=True)
        return None
