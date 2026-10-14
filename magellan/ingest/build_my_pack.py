"""Build magellan/packs/MY.json from official Malaysian sources.

Rules are cut verbatim (between two anchor phrases) from Bank Negara Malaysia's Policy Document on
Medical and Health Insurance/Takaful Business (PD MHIT, BNM/RH/PD 029-..., revised Dec 2025) and
the Financial Markets Ombudsman Service (FMOS) FAQ, so the checker can verify quotes.
The Financial Services Act 2013 (Schedule 9, duty of disclosure) is not included: BNM's site
offers no machine-readable text and we only store rules we can quote word for word.
Run from the repo root:  python3 magellan/ingest/build_my_pack.py
"""

import html
import io
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "packs" / "MY.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/126 Safari/537.36"

PD_MHIT = "https://www.bnm.gov.my/documents/20124/938039/pd_mhit_dec25.pdf"
FMOS_FAQ = "https://www.fmos.org.my/en/faq/"

# (ref, title, url, first words, last words)
SECTIONS = [
    (
        "BNM PD MHIT para 9.6(a)",
        "General (initial) waiting period for all illnesses: at most 30 days; none for accidents",
        PD_MHIT,
        "(a) The general waiting period shall not",
        "arising from an accident;",
    ),
    (
        "BNM PD MHIT para 9.6(b)",
        "Other waiting periods: only for illnesses listed in the Glossary of Terms, at most 120 days",
        PD_MHIT,
        "(b) Imposition of any additional waiting period",
        "from the effective date of the MHIT policy/takaful certificate;",
    ),
    (
        "BNM PD MHIT para 9.6(c)",
        (
            "Pre-existing conditions: only those existing before cover that the patient could "
            "reasonably have known about; the insurer must prove it"
        ),
        PD_MHIT,
        "(c) Any coverage exclusions or limitations for pre-existing condition(s)",
        "denies a claim of an excluded pre-existing condition;",
    ),
    (
        "BNM PD MHIT para 9.6(c), footnote 14",
        "When a patient is considered to have been reasonably aware of a pre-existing condition",
        PD_MHIT,
        "A policy owner/takaful participant may be considered to have reasonably been aware",
        "apparent to a reasonable person in the circumstances.",
    ),
    (
        "BNM PD MHIT para 13.8",
        "Exclusions and limitations must be set out in the policy",
        PD_MHIT,
        "13.8 A licensed ITO shall provide complete information",
        "switching of products or plans.",
    ),
    (
        "FMOS FAQ Q4",
        "FMOS: when you can file (6 months from the final decision, or no reply in 60 days)",
        FMOS_FAQ,
        "You must file an official complaint against the FMOS Members.",
        "from the date the complaint was first submitted to the Member concerned.",
    ),
    (
        "FMOS FAQ Q5-Q6",
        "FMOS: free of charge; medical claims up to RM250,000",
        FMOS_FAQ,
        "No. Our service is provided free of charge",
        "third-party property damage claims.",
    ),
    (
        "FMOS FAQ Q19",
        "FMOS: the Ombudsman's decision binds the insurer, not the patient",
        FMOS_FAQ,
        "The Ombudsman’s Decision is binding only on FMOS Members.",
        "they can explore other avenues to resolve their dispute.",
    ),
]

# pypdf splits some words ("a ny", "pre - existing"); repair only the patterns seen in PD MHIT.
PDF_FIXES = [
    (r"\ba ny\b", "any"),
    (r"\bpre ?- ?existing\b", "pre-existing"),
    (r"\breasonabl y\b", "reasonably"),
    (r"\banti ?- ?selection\b", "anti-selection"),
    (r"\bGOT ,", "GOT,"),
    (r"\bITO s\b", "ITOs"),
]

FMOS_FIELDS = [
    ("Financial service provider (insurer or takaful operator)", "facts.insurer"),
    ("Your name", "complainant.name"),
    ("Contact number", "complainant.mobile"),
    ("Email", "complainant.email"),
    ("Address", "complainant.address"),
    ("Relationship to the insured person", "complainant.relationship_to_insured"),
    ("Policy / certificate number", "facts.policy_number"),
    ("Claim number", "facts.claim_number"),
    ("Details of the dispute", "generated.summary"),
    ("Date you complained to the insurer", "complainant.grievance_date"),
    ("Date of the insurer's final decision", "complainant.grievance_reply_date"),
    ("Amount in dispute (FMOS limit RM250,000)", "computed.relief"),
    ("Proceedings in court or arbitration on the same matter", "complainant.court_proceedings"),
    ("Supporting documents (insurer's letters, medical reports, bills)", "computed.enclosures"),
]


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=60).read()


def _pdf_text(url: str) -> str:
    from pypdf import PdfReader  # sombrero's venv has it

    reader = PdfReader(io.BytesIO(_fetch(url)))
    text = re.sub(r"\s+", " ", " ".join(p.extract_text() or "" for p in reader.pages))
    for pattern, repl in PDF_FIXES:
        text = re.sub(pattern, repl, text)
    # Footnote markers glued to words ("aware of 14.") would break quotes; drop them.
    return re.sub(r"aware of 14\. ", "aware of. ", text)


def _page(url: str) -> str:
    raw = _fetch(url).decode("utf-8", "ignore")
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.DOTALL)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))


def _cut(page: str, start: str, end: str) -> str:
    i = page.index(start)
    j = page.index(end, i) + len(end)
    return page[i:j].strip()


def main() -> None:
    pages: dict[str, str] = {}
    children = []
    for ref, title, url, start, end in SECTIONS:
        if url not in pages:
            pages[url] = _pdf_text(url) if url.endswith(".pdf") else _page(url)
        children.append(
            {"ref": ref, "title": title, "source_url": url, "text": _cut(pages[url], start, end)}
        )
    pack = {
        "country": "MY",
        "currency": "MYR",
        "languages": ["en", "ms", "zh", "ta"],
        "regulator": "BNM",
        "rejection_codes": {},
        "dispute_process": [
            {
                "step": "Insurer's complaints unit",
                "dispute_body": "The insurer's or takaful operator's complaints unit",
                # FMOS takes the dispute if the insurer has not replied within 60 days.
                "deadline_days": 60,
                "form": "Appeal letter",
                "form_fields": [],
            },
            {
                "step": "FMOS",
                "dispute_body": "Financial Markets Ombudsman Service (FMOS), www.fmos.org.my",
                "deadline_days": 180,
                "form": "FMOS dispute form",
                "form_fields": [{"label": lbl, "source": src} for lbl, src in FMOS_FIELDS],
                "relief_note": "(FMOS can award up to RM250,000)",
            },
        ],
        # FMOS: within 6 months of the insurer's final decision.
        "limitation": {"days": 183, "body": "FMOS", "from": "the insurer's final decision"},
        "regulations": [
            {
                "ref": "Malaysia medical-insurance claim rules (BNM PD MHIT, FMOS)",
                "children": children,
            }
        ],
    }
    PACK.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for c in children:
        print(f"{c['ref']:<40} {len(c['text']):>4} chars")


if __name__ == "__main__":
    main()
