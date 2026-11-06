"""Photo check at upload: is this phone photo readable enough to build a case on?

Runs before analysis so the patient can retake a bad photo while they still have the
paper in hand, instead of learning after a failed analysis. Fail-open: any error or a
slow model means no warning, never a blocked upload.
"""

import asyncio
import logging
from enum import StrEnum

from pydantic import BaseModel

from ..config import get_settings
from . import llm

log = logging.getLogger(__name__)

PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
TIMEOUT_SECONDS = 12


class PhotoIssue(StrEnum):
    OK = "ok"
    BLURRY = "blurry"
    CUT_OFF = "cut_off"
    TOO_DARK = "too_dark"
    GLARE = "glare"
    NOT_A_DOCUMENT = "not_a_document"


class PhotoCheck(BaseModel):
    issue: PhotoIssue


PROMPT = """You check one phone photo that a patient uploaded for a health-insurance claim dispute.
Decide whether the text in it can be read reliably. Answer with exactly one issue:
- ok: a document (letter, policy, bill, discharge summary, prescription, report) and its text is readable
- blurry: out of focus or motion-blurred so words are hard to read
- cut_off: part of the page is outside the photo, so text at an edge is missing
- too_dark: underexposed or in shadow so text is hard to read
- glare: a reflection or flash hides part of the text
- not_a_document: not a paper or screen showing a document (a person, a room, an object)
Be lenient: small imperfections that still leave every word readable are ok."""


def check_photo(uri: str) -> PhotoIssue:
    return llm.structured(PROMPT, [uri], PhotoCheck, model=get_settings().model_fast).issue


async def photo_issue(uri: str) -> PhotoIssue | None:
    """The problem with this photo, or None when it is fine or could not be checked."""
    try:
        issue = await asyncio.wait_for(asyncio.to_thread(check_photo, uri), TIMEOUT_SECONDS)
    except Exception:
        # Degraded, not broken: the upload still succeeds without a warning.
        log.warning("photo check skipped", exc_info=True)
        return None
    return None if issue == PhotoIssue.OK else issue
