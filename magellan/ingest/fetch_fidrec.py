"""Download FIDReC's published case studies into magellan/sources/sg/fidrec/case_studies.json.

FIDReC has no index page, so this walks the knowledge-base article ids politely.
Run from the repo root:  python3 magellan/ingest/fetch_fidrec.py
"""

import concurrent.futures as cf
import html
import json
import re
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "sources" / "sg" / "fidrec" / "case_studies.json"
DISCLAIMER = "not necessarily indicative of outcomes at FIDReC."


def fetch(n: int) -> dict | None:
    url = f"https://www.fidrec.com.sg/knowledgebase/article/KA-0{n}/en-us"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    except OSError:  # URLError, HTTPError and timeouts all subclass OSError
        return None
    finally:
        time.sleep(0.3)
    title = re.search(r"<title>(.*?)</title>", page, re.DOTALL)
    title = (
        " ".join(html.unescape(title.group(1)).split()).replace(" · FIDReC", "") if title else ""
    )
    if "Case Study" not in title:
        return None
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.DOTALL)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))
    start, end = text.find(DISCLAIMER), text.find("Was this article helpful")
    body = text[start + len(DISCLAIMER) : end if end > 0 else None].strip() if start > 0 else ""
    return {"ka": f"KA-0{n}", "url": url, "title": title, "text": body}


def main() -> None:
    with cf.ThreadPoolExecutor(4) as pool:
        found = [r for r in pool.map(fetch, range(1000, 1400)) if r]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(found, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(found)} case studies -> {OUT}")


if __name__ == "__main__":
    main()
