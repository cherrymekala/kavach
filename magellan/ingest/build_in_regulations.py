"""Build the IN pack's `regulations` outline from the IRDAI PDFs in magellan/sources/regulations.

Section text is copied verbatim (whitespace normalised) so the checker can verify quotes.
Run from the repo root after fetch_sources.sh:  python3 magellan/ingest/build_in_regulations.py
"""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGS = ROOT / "magellan" / "sources" / "regulations"
PACK = ROOT / "magellan" / "packs" / "IN.json"
NOISE = re.compile(
    r"^\s*(Page \d+ of \d+|\[भाग.*|\d+\s+THE GAZETTE OF INDIA.*|Uploaded by .*|and Published by .*)\s*$"
)


def _text(pdf: str) -> list[str]:
    out = subprocess.run(
        ["pdftotext", "-layout", str(REGS / pdf), "-"], capture_output=True, text=True, check=True
    )
    return [line for line in out.stdout.splitlines() if not NOISE.match(line)]


def _clean(lines: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(lines)).strip().lstrip(": ")


def _split(lines: list[str], head: re.Pattern) -> list[tuple[str, str, str]]:
    """Split lines at each heading match -> (number, title, text)."""
    marks = [(i, m) for i, line in enumerate(lines) if (m := head.match(line))]
    parts = []
    for k, (i, m) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        body = _clean([m.group(3)] + lines[i + 1 : end])
        parts.append((m.group(1), m.group(2).strip(" :-–"), body))
    return parts


def products_regulations() -> dict:
    lines = _text("IRDAI_Insurance_Products_Regulations_2024.pdf")
    start = next(
        i
        for i, line in enumerate(lines)
        if "Schedule III: Specific provisions applicable to health" in line
    )
    sched = [
        line
        for line in lines[start + 1 :]
        if "Digitally signed" not in line and "KUMAR VERMA" not in line
    ]
    definition = re.compile(r"^\s*(1\.\d)\.\s+(“[^”]+”)(.*)$")
    section = re.compile(r"^\s*(\d{1,2})\.\s+([A-Z][^:]{3,120}?)\s*(?::(.*))?$")
    marks = []
    for i, line in enumerate(sched):
        if m := definition.match(line):
            marks.append(
                (i, m.group(1), f"Definition of {m.group(2).strip('“”')}", m.group(2) + m.group(3))
            )
        elif (m := section.match(line)) and m.group(1) != "1":
            marks.append((i, m.group(1), m.group(2), m.group(3) or ""))
    children = []
    for k, (i, num, title, first) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(sched)
        children.append(
            {
                "ref": f"Products Regulations 2024, Sch. III, cl. {num}",
                "title": title,
                "text": _clean([first] + sched[i + 1 : end]),
            }
        )
    return {
        "ref": "IRDAI (Insurance Products) Regulations, 2024 — Schedule III (Health)",
        "children": children,
    }


def master_circular() -> dict:
    lines = _text("IRDAI_Health_Master_Circular_2024.pdf")
    start = next(
        i
        for i, line in enumerate(lines)
        if line.strip().startswith("Chapter I: General Information")
    )
    end = next(
        i
        for i, line in enumerate(lines)
        if line.strip().startswith("Chapter II: Broad Requirements")
    )
    chapter = lines[start + 1 : end]
    paras = []
    titles = {"1": "Products for all ages, conditions and treatments"}
    for num, title, body in _split(chapter, re.compile(r"^\s*(\d{1,2})\)\s+(.*?)(:?)\s*$")):
        if num in titles:
            body, title = f"{title} {body}".strip(), titles[num]
        paras.append(
            {
                "ref": f"Health Master Circular 2024, Ch. I, para {num}",
                "title": re.sub(r"\s+", " ", title),
                "text": body,
            }
        )
    claims = next(
        i for i, line in enumerate(lines) if "(4) Claims Handling and Settlement process" in line
    )
    stop = next(i for i, line in enumerate(lines) if "(5) Display on Insurers Website" in line)
    paras.append(
        {
            "ref": "Health Master Circular 2024, Ch. II, A.I(4)",
            "title": "Claims handling and Claims Review Committee",
            "text": _clean(lines[claims + 1 : stop]),
        }
    )
    return {
        "ref": "IRDAI Master Circular on Health Insurance Business, 2024 (IRDAI/HLT/CIR/PRO/84/5/2024)",
        "children": paras,
    }


def _between(lines: list[str], start: str, end: str, after: int = 0) -> tuple[int, list[str]]:
    i = next(k for k, line in enumerate(lines) if k >= after and line.strip().startswith(start))
    j = next(k for k, line in enumerate(lines) if k > i and line.strip().startswith(end))
    return i, lines[i + 1 : j]


def standardization() -> dict:
    lines = _text("IRDAI_Standardization_Master_Circular_2020.pdf")
    doc = "Standardization MC 2020"
    children = []

    _, defs = _between(
        lines, "Chapter I: Standard Definitions", "Chapter II: Standard Nomenclature"
    )
    head = re.compile(r"^\s*(\d{1,2})\s*\.\s+([A-Z][^:(]{2,70}?)\s*:?\s*(?:\(.*)?:?\s*$")
    marks = [
        (i, m.group(1), m.group(2).strip())
        for i, line in enumerate(defs)
        if (m := head.match(line))
    ]
    for k, (i, num, title) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(defs)
        children.append(
            {
                "ref": f"{doc}, Standard Definition {num}",
                "title": f"Definition of {title}",
                "text": _clean(defs[i + 1 : end]),
            }
        )

    at, banned = _between(
        lines, "Chapter II: Exclusions not allowed", "Chapter III: Standard Wordings"
    )
    children.append(
        {
            "ref": f"{doc}, Exclusions not allowed",
            "title": "Exclusions insurers may not use",
            "text": _clean(banned),
        }
    )

    _, excl = _between(
        lines, "Chapter III: Standard Wordings", "Chapter IV: Existing Diseases", after=at
    )
    head = re.compile(r"^\s*([A-R])\.\s+(.*)$")
    marks = [(i, m.group(2)) for i, line in enumerate(excl) if (m := head.match(line))]
    for k, (i, first) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(excl)
        body = _clean([first] + excl[i + 1 : end])
        code = re.search(r"Code\s*[-–]?\s*Excl\s*(\d+)", body)
        name = re.sub(r"^Exclusion Name:\s*", "", first).split("Code")[0].strip(" :-–")
        ref = f"{doc}, Excl{code.group(1)}" if code else f"{doc}, Exclusion {first[:20]}"
        children.append({"ref": ref, "title": f"Standard exclusion: {name}", "text": body})
    return {
        "ref": "IRDAI Master Circular on Standardization of Health Insurance Products, 2020 (IRDAI/HLT/REG/CIR/193/07/2020)",
        "children": children,
    }


def main() -> None:
    pack = json.loads(PACK.read_text(encoding="utf-8"))
    pack["regulations"] = [products_regulations(), master_circular(), standardization()]
    PACK.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for root in pack["regulations"]:
        print(root["ref"])
        for c in root["children"]:
            print(f"  {c['ref']:<52} {c['title'][:45]:<45} {len(c['text']):>5} chars")


if __name__ == "__main__":
    main()
