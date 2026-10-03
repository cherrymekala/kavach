"""Filing agent: the appeal letter and the official form for the current dispute step.

Form fields come from the country pack (`dispute_process[].form_fields`), so a new country's
form is data, not code. Only the case summary is written by Gemini; everything else is filled
from facts or what the patient told us, and unknown values stay blank to fill by hand.
"""

from datetime import UTC, datetime
from pathlib import Path

from fpdf import FPDF
from pydantic import BaseModel

from ..config import get_settings
from ..models import Case, Complainant, FilingPack, Letter
from ..tools import packs
from . import llm, prompts


def _context(case: Case) -> dict:
    arguments = case.assessment.arguments if case.assessment else []
    steps = packs.load(case.country)["dispute_process"]
    return {
        "facts": case.facts.model_dump(mode="json") if case.facts else {},
        "arguments": [a.model_dump(mode="json") for a in arguments],
        "country": case.country,
        "recipient": steps[0]["dispute_body"],
        "reply_days": steps[0]["deadline_days"],
        "next_dispute_body": steps[1]["step"] if len(steps) > 1 else None,
        "complaint_to": steps[-1]["dispute_body"],
    }


def draft_letter(case: Case, instruction: str | None = None) -> Letter:
    context = {
        **_context(case),
        "language": case.language,
        "today": datetime.now(UTC).date().isoformat(),
    }
    if instruction:
        context["revision_request"] = instruction
        context["previous_letter"] = case.letter.english if case.letter else None
    letter = llm.structured(prompts.LETTER, [], Letter, context=context)
    # Models sometimes return escaped newlines or skip the translation; repair both.
    letter.english = letter.english.replace("\\n", "\n")
    if case.language == "en":
        letter.local = None
    elif not (letter.local or "").strip():
        letter.local = llm.text(
            prompts.TRANSLATE_LETTER, {"language": case.language, "letter": letter.english}
        )
    if letter.local:
        letter.local = letter.local.replace("\\n", "\n")
    letter.language = case.language
    return letter


def _indian(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ",".join([head, *groups, tail]) if head else ",".join([*groups, tail])


def _money(amount: float | None, currency: str | None) -> str:
    if amount is None:
        return ""
    if currency == "INR":
        return f"Rs. {_indian(round(amount))}"
    symbol = {"SGD": "S$"}.get(currency or "", currency or "")
    return f"{symbol} {amount:,.0f}".strip()


def _computed(case: Case, key: str, template: dict | None = None) -> str:
    f = case.facts
    if not f:
        return ""
    unpaid = (f.claim_amount or 0) - (f.amount_approved or 0) if f.claim_amount else None
    if key == "loss":
        if unpaid is None:
            return ""
        kind = "partially settled" if f.amount_approved else "rejected"
        return f"Claim of {_money(f.claim_amount, f.currency)} {kind}; unpaid {_money(unpaid, f.currency)}"
    if key == "relief":
        note = (template or {}).get("relief_note", "")
        return f"Payment of {_money(unpaid, f.currency)} {note}".strip() if unpaid else ""
    if key == "enclosures":
        names = [d.filename for d in case.documents]
        return "; ".join(["Appeal letter to the insurer", "Insurer's reply (if any)", *names])
    return ""


def _value(case: Case, complainant: Complainant, source: str, summary: str, template: dict) -> str:
    kind, _, key = source.partition(".")
    if source.startswith("const:"):
        return source[6:]
    if kind == "generated":
        return summary
    if kind == "computed":
        return _computed(case, key, template)
    obj = case.facts if kind == "facts" else complainant
    value = getattr(obj, key, None) if obj else None
    if isinstance(value, bool):
        return "Ported" if value else "Fresh"
    return "" if value is None else str(value)


class _Office(BaseModel):
    centre: str | None


def pick_office(country: str, offices_key: str | None, address: str | None) -> dict | None:
    offices = packs.load(country).get(offices_key or "", [])
    if not offices or not address:
        return None
    listing = [{"centre": o["centre"], "jurisdiction": o["jurisdiction"]} for o in offices]
    choice = llm.structured(
        prompts.PICK_OFFICE,
        [],
        _Office,
        context={"address": address, "offices": listing},
        model=get_settings().model_fast,
    )
    return next((o for o in offices if o["centre"] == choice.centre), None)


def filing_pack(case: Case, step: int | None = None) -> FilingPack:
    process = packs.load(case.country)["dispute_process"]
    template = process[min(case.escalation_step if step is None else step, len(process) - 1)]
    complainant = case.complainant or Complainant()
    needs_summary = any(f["source"] == "generated.summary" for f in template["form_fields"])
    summary = (
        llm.text(prompts.COMPLAINT_SUMMARY, _context(case), model=get_settings().model_reasoning)
        if needs_summary
        else ""
    )
    fields = [
        {
            "label": f["label"],
            "value": _value(case, complainant, f["source"], summary, template).strip(),
        }
        for f in template["form_fields"]
    ]
    body = template.get("dispute_body", template["step"])
    office = pick_office(case.country, template.get("offices"), complainant.address)
    if office:
        body = f"Insurance Ombudsman, {office['centre']}: {office['address']} (Email: {office['email']})"
    return FilingPack(
        form=template["form"],
        dispute_body=body,
        fields=fields,
        missing=[f["label"] for f in fields if not f["value"]],
    )


FONTS = Path(__file__).resolve().parents[1] / "fonts"
_SCRIPTS = (
    "NotoSansDevanagari",
    "NotoSansTamil",
    "NotoSansTelugu",
    "NotoSansSC",
)  # hi/mr, ta, te, zh
_NOTE = "Prepared with Kavach from your documents. Check every detail before signing. This is not legal advice."


def _pdf() -> FPDF:
    pdf = FPDF(format="A4")
    pdf.add_font("NotoSans", "", FONTS / "NotoSans-Regular.ttf")
    pdf.add_font("NotoSans", "B", FONTS / "NotoSans-Bold.ttf")
    for name in _SCRIPTS:
        pdf.add_font(name, "", FONTS / f"{name}-Regular.ttf")
    # Characters missing from Noto Sans fall through to the right Indic font; HarfBuzz joins them.
    pdf.set_fallback_fonts(list(_SCRIPTS), exact_match=False)
    pdf.set_text_shaping(True)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    return pdf


def _para(pdf: FPDF, text: str, size: int = 10, style: str = "", height: float = 6) -> None:
    pdf.set_font("NotoSans", style, size)
    pdf.multi_cell(0, height, text, new_x="LMARGIN", new_y="NEXT")


def render_pdf(pack: FilingPack, case: Case) -> bytes:
    pdf = _pdf()
    _para(pdf, pack.form, 13, "B", 7)
    _para(pdf, f"To: {pack.dispute_body}")
    pdf.ln(3)
    for field in pack.fields:
        _para(pdf, field["label"], style="B")
        _para(pdf, field["value"] or "______________________________________________")
        pdf.ln(2)
    if case.letter and pack.form.startswith("Appeal letter"):
        _para(pdf, case.letter.english)
    pdf.ln(4)
    _para(pdf, _NOTE, 8, height=5)
    pdf.ln(8)
    _para(pdf, "Signature of the complainant: ____________________    Date: ____________")
    return bytes(pdf.output())


def render_letter_pdf(letter: Letter, local: bool = False) -> bytes:
    pdf = _pdf()
    _para(pdf, letter.subject, 11, "B")
    pdf.ln(3)
    _para(pdf, (letter.local if local and letter.local else letter.english), height=6.5)
    pdf.ln(4)
    _para(pdf, _NOTE, 8, height=5)
    return bytes(pdf.output())
