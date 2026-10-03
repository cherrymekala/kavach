"""Checker agent: keep only sources whose quote really appears in the cited source.

1. Deterministic: normalised substring match against regulation text, ruling summaries and
   the extracted text of the case documents.
2. Gemini fallback, only for document quotes step 1 could not confirm (e.g. scanned files).
Sources that fail are dropped; arguments left without a verified source are dropped.
"""

import re

from pydantic import BaseModel

from ..config import get_settings
from ..models import Assessment, Document
from ..tools import texts
from . import llm, prompts

DOC_KINDS = {"policy", "rejection_letter", "discharge_summary", "bill"}
_PUNCT = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})


def _norm(text: str) -> str:
    text = text.translate(_PUNCT).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9.%₹ ]", " ", text)).strip()


def _in_order(parts: list[str], hay: str) -> bool:
    pos = 0
    for p in parts:
        i = hay.find(p, pos)
        if i < 0:
            return False
        pos = i + len(p)
    return True


def quote_in(quote: str, text: str) -> bool:
    parts = [p for p in (_norm(x) for x in re.split(r"\.\.\.|…", quote)) if p]
    if not parts or not text:
        return False
    hay = _norm(text)
    # PDF extraction sometimes drops or adds spaces between words, so retry without spaces.
    return _in_order(parts, hay) or _in_order([p.replace(" ", "") for p in parts], hay.replace(" ", ""))


class _Check(BaseModel):
    index: int
    found: bool


class _Checks(BaseModel):
    results: list[_Check]


def _gemini_check(pending: list[tuple[int, int, str]], documents: list[Document]) -> set[int]:
    """pending: (item id, file index, quote) -> ids Gemini confirmed."""
    if not pending:
        return set()
    items = [{"index": i, "file_index": f, "quote": q} for i, f, q in pending]
    out = llm.structured(
        prompts.CHECKER,
        [d.gcs_uri for d in documents],
        _Checks,
        context={"items": items},
        model=get_settings().model_fast,
    )
    return {c.index for c in out.results if c.found}


def verify(
    assessment: Assessment, documents: list[Document], sections: list[dict], similar: list[dict]
) -> Assessment:
    regs = {s["ref"]: s["text"] for s in sections}
    rulings = {
        r["id"]: " ".join(str(r.get(k) or "") for k in ("summary", "diagnosis", "insurer"))
        for r in similar
    }
    doc_text = {i: texts.read(d.gcs_uri) for i, d in enumerate(documents)}

    sources = [s for a in assessment.arguments for s in a.sources]
    pending = []
    for n, src in enumerate(sources):
        if src.kind == "regulation":
            src.verified = quote_in(src.quote, regs.get(src.ref, ""))
        elif src.kind == "ruling":
            src.verified = quote_in(src.quote, rulings.get(src.ref, ""))
        elif src.kind in DOC_KINDS:
            files = [i for i, d in enumerate(documents) if d.doc_type == src.kind] or list(doc_text)
            src.verified = any(quote_in(src.quote, doc_text[i]) for i in files)
            if not src.verified:
                pending += [(n * 100 + i, i, src.quote) for i in files]
    confirmed = {key // 100 for key in _gemini_check(pending, documents)}
    for n in confirmed:
        sources[n].verified = True

    kept = []
    for arg in assessment.arguments:
        good = [s for s in arg.sources if s.verified]
        if good:
            kept.append(arg.model_copy(update={"sources": good}))
    return assessment.model_copy(update={"arguments": kept})
