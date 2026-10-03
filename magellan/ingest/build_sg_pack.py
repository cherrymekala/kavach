"""Build magellan/packs/SG.json from official Singapore sources.

Regulation text is cut verbatim from the official pages (between two anchor phrases) so the
checker can verify quotes. Run from the repo root:  python3 magellan/ingest/build_sg_pack.py
"""

import html
import json
import re
import urllib.request
from pathlib import Path

PACK = Path(__file__).resolve().parents[2] / "magellan" / "packs" / "SG.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/126 Safari/537.36"

MAS_PQ = "https://www.mas.gov.sg/news/parliamentary-replies/2022/reply-to-parliamentary-question-on-complaints-about-unsuccessful-medical-insurance-claims"
MOH_ND = "https://www.moh.gov.sg/newsroom/denial-of-medishield-life-claims-due-to-non-disclosure-of-minor-unrelated-health-conditions/"
FIDREC_GUIDE = "https://www.fidrec.com.sg/knowledgebase/article/KA-01259/en-us"
FIDREC_FAQ = "https://www.fidrec.com.sg/knowledgebase/article/KA-01013"

# (ref, title, url, first words, last words)
SECTIONS = [
    (
        "MAS reply to PQ, 12 Jan 2022, para 1",
        "MAS: insurers must be fair; no rejection for minor unrelated conditions",
        MAS_PQ,
        "MAS expects insurers to be fair and reasonable",
        "minor and unrelated conditions.",
    ),
    (
        "MAS reply to PQ, 12 Jan 2022, para 3",
        "MAS: non-disclosure must be material and reasonably expected",
        MAS_PQ,
        "To reject a claim on grounds of non-disclosure",
        "application for the policy.",
    ),
    (
        "MAS reply to PQ, 12 Jan 2022, para 4",
        "Redress: FIDReC and the Clinical Claims Resolution Process",
        MAS_PQ,
        "Policyholders who feel their claims have been unfairly rejected",
        "by medical practitioners.",
    ),
    (
        "MOH written answer, 13 Sep 2021",
        "MOH: MediShield Life covers pre-existing conditions; IP insurers must not reject for minor unrelated conditions",
        MOH_ND,
        "MediShield Life does not deny claims due to non-disclosure",
        "minor and unrelated.",
    ),
    (
        "FIDReC Consumer's Guide to Life Insurance Disputes, Step 2",
        "FIDReC: when you can file (after 4 weeks) and mediation",
        FIDREC_GUIDE,
        "If you cannot resolve the matter with your insurer after 4 weeks",
        "There is no cost to consumers to do so.",
    ),
    (
        "FIDReC Consumer's Guide to Life Insurance Disputes, limitations",
        "FIDReC: S$150,000 adjudication limit and 6-month time limit",
        FIDREC_GUIDE,
        "Claims that exceed S$150,000",
        "to ensure that FIDReC is able to assist you.",
    ),
    (
        "FIDReC FAQ Q10",
        "FIDReC: adjudication jurisdiction per claim",
        FIDREC_FAQ,
        "The jurisdiction of FIDReC in adjudicating disputes",
        "on or after 1 July 2024).",
    ),
]

FIDREC_FIELDS = [
    ("Financial institution complained against", "facts.insurer"),
    ("Your name", "complainant.name"),
    ("Contact number", "complainant.mobile"),
    ("Email", "complainant.email"),
    ("Address", "complainant.address"),
    ("Relationship to the insured person", "complainant.relationship_to_insured"),
    ("Policy number", "facts.policy_number"),
    ("Claim number", "facts.claim_number"),
    ("Details of your complaint, including what has happened so far", "generated.summary"),
    ("Date you complained to the insurer", "complainant.grievance_date"),
    ("Date of the insurer's final reply", "complainant.grievance_reply_date"),
    ("Amount claimed (adjudication limit S$150,000)", "computed.relief"),
    ("Proceedings in court or elsewhere on the same matter", "complainant.court_proceedings"),
    ("Supporting documents (medical reports, invoices, insurer letters)", "computed.enclosures"),
]


def _page(url: str) -> str:
    raw = urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30
    ).read()
    text = re.sub(
        r"<script.*?</script>|<style.*?</style>", "", raw.decode("utf-8", "ignore"), flags=re.DOTALL
    )
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))


def _cut(page: str, start: str, end: str) -> str:
    i = page.index(start)
    j = page.index(end, i) + len(end)
    return page[i:j].strip()


def main() -> None:
    pages: dict[str, str] = {}
    children = []
    for ref, title, url, start, end in SECTIONS:
        page = pages.setdefault(url, _page(url))
        children.append(
            {"ref": ref, "title": title, "source_url": url, "text": _cut(page, start, end)}
        )
    pack = {
        "country": "SG",
        "currency": "SGD",
        "languages": ["en", "zh", "ms", "ta"],
        "regulator": "MAS",
        "rejection_codes": {},
        "dispute_process": [
            {
                "step": "Insurer's internal dispute resolution",
                "dispute_body": "The insurer's customer service / claims appeal team",
                "deadline_days": 28,
                "form": "Appeal letter",
                "form_fields": [],
            },
            {
                "step": "FIDReC",
                "dispute_body": "Financial Industry Disputes Resolution Centre (FIDReC), www.fidrec.com.sg",
                "deadline_days": 180,
                "form": "FIDReC online complaint",
                "form_fields": [
                    {"label": label, "source": source} for label, source in FIDREC_FIELDS
                ],
            },
        ],
        # Must approach FIDReC within 6 months of the insurer's final reply.
        "limitation": {"days": 183, "body": "FIDReC", "from": "the insurer's final reply"},
        "regulations": [
            {
                "ref": "Singapore health-insurance claim rules (MAS, MOH, FIDReC)",
                "children": children,
            }
        ],
    }
    PACK.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for c in children:
        print(f"{c['ref']:<62} {len(c['text']):>4} chars")


if __name__ == "__main__":
    main()
