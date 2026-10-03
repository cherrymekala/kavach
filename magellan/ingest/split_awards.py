"""Split Ombudsman award books (magellan/sources/awards/txt) into one JSONL record per award.

Output: magellan/sources/rulings.jsonl (git-ignored), fields:
id, country, source, case_no, award_date, insurer, decision, text.
Category and summary are added later by label_rulings.py.
"""
import hashlib
import json
import re
from datetime import date
from pathlib import Path

SOURCES = Path(__file__).resolve().parents[1] / "sources"
AWARD_DATE = re.compile(r"award\s*dat(?:ed|e)\s*[:\-]?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", re.IGNORECASE)
CASE_NO = re.compile(r"(?:case|complaint)\s*no\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9 ./\-]{4,40})", re.IGNORECASE)
# Some offices open an award with this header and print no "Award Dated" line.
HEADER = re.compile(r"(?:office of the|before the)\s+insurance\s+ombudsman", re.IGNORECASE)

INSURERS = {
    "New India Assurance": r"new india|\bNIA\b",
    "Oriental Insurance": r"oriental|\bOIC\b",
    "United India Insurance": r"united india|\bUII\b|\bUIIC\b",
    "National Insurance": r"national insurance|\bNIC\b",
    "Star Health": r"star health",
    "ICICI Lombard": r"icici lombard",
    "Bajaj Allianz": r"bajaj allianz",
    "HDFC ERGO": r"hdfc ergo",
    "Apollo Munich": r"apollo munich",
    "Max Bupa": r"max bupa",
    "Religare": r"religare",
    "Tata AIG": r"tata aig",
    "Reliance General": r"reliance general",
    "Cholamandalam MS": r"cholamandalam",
    "IFFCO Tokio": r"iffco",
    "Royal Sundaram": r"royal sundaram",
    "Future Generali": r"future generali",
    "SBI General": r"sbi general",
    "Universal Sompo": r"universal sompo",
}

ALLOWED = re.compile(r"complaint\s+(?:is|stands|was)?\s*(?:hereby\s+)?(?:,\s*thus,\s*)?allowed|direct(?:ed)?\s+(?:the\s+)?(?:respondent|insurer|insurance\s+company)\s+to\s+(?:pay|settle|make)", re.IGNORECASE)
PARTLY = re.compile(r"partly\s+allowed|partially\s+allowed|ex[- ]gratia", re.IGNORECASE)
DISMISSED = re.compile(r"(?:complaint|petition)\s+(?:is|stands|was)?\s*(?:hereby\s+)?dismissed|no\s+relief|without\s+any\s+relief|not\s+sustainable|devoid\s+of\s+merit", re.IGNORECASE)


def _date(d: str, m: str, y: str) -> str | None:
    year = int(y) + (2000 if len(y) == 2 else 0)
    try:
        return date(year, int(m), int(d)).isoformat()
    except ValueError:
        return None


def _insurer(text: str) -> str | None:
    head = text[:3000]
    for name, pat in INSURERS.items():
        if re.search(pat, head, re.IGNORECASE):
            return name
    return None


def _decision(text: str) -> str:
    tail = text[-2500:]
    if PARTLY.search(tail):
        return "partly_allowed"
    allowed, dismissed = ALLOWED.search(tail), DISMISSED.search(tail)
    if allowed and dismissed:
        return "allowed" if allowed.start() > dismissed.start() else "dismissed"
    return "allowed" if allowed else "dismissed" if dismissed else "unknown"


def split_book(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    starts: list[int] = []
    for i, line in enumerate(lines):
        if HEADER.search(line):
            start = i
        elif AWARD_DATE.search(line):
            start = i
            for j in range(i - 1, max(i - 9, -1), -1):
                if HEADER.search(lines[j]) or CASE_NO.search(lines[j]):
                    start = j
                    if HEADER.search(lines[j]):
                        break
        else:
            continue
        # A header followed within a few lines by its case no / award date is one award.
        if not starts or start > starts[-1] + 12:
            starts.append(start)
    records = []
    for k, s in enumerate(starts):
        chunk = "\n".join(lines[s : starts[k + 1] if k + 1 < len(starts) else len(lines)]).strip()
        chunk = re.sub(r"[ \t]{2,}", " ", chunk)
        if len(chunk) < 600:
            continue
        d = AWARD_DATE.search(chunk)
        c = CASE_NO.search(chunk[:400])
        records.append({
            "id": "in-ombud-" + hashlib.sha1(chunk[:1500].encode()).hexdigest()[:12],
            "country": "IN",
            "source": f"CIO {path.stem}",
            "case_no": c.group(1).strip() if c else None,
            "award_date": _date(*d.groups()) if d else None,
            "insurer": _insurer(chunk),
            "decision": _decision(chunk),
            "text": chunk[:20000],
        })
    return records


def main() -> None:
    seen, out = set(), []
    for book in sorted((SOURCES / "awards" / "txt").glob("*.txt")):
        for r in split_book(book):
            if r["id"] not in seen:
                seen.add(r["id"])
                out.append(r)
    dest = SOURCES / "rulings.jsonl"
    dest.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    counts: dict[str, int] = {}
    for r in out:
        counts[r["decision"]] = counts.get(r["decision"], 0) + 1
    print(f"{len(out)} awards -> {dest}")
    print("decisions:", counts)
    print("with insurer:", sum(1 for r in out if r["insurer"]), "with date:", sum(1 for r in out if r["award_date"]))


if __name__ == "__main__":
    main()
