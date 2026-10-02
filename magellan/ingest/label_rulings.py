"""Label each award in magellan/sources/rulings.jsonl with Gemini (decision, category, summary).

Resumable: appends to rulings_labels.jsonl and skips ids already labelled.
Run from the repo root (Vertex is far faster than the free tier):
    USE_VERTEX=true sombrero/.venv/bin/python magellan/ingest/label_rulings.py
"""
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import BaseModel

from kavach.agents.llm import client
from kavach.config import get_settings
from kavach.models import RejectionCategory

SOURCES = Path(__file__).resolve().parents[1] / "sources"
BATCH = 15
WORKERS = int(os.environ.get("LABEL_WORKERS", "1"))
MAX_CHARS = 6000

PROMPT = """You label Indian Insurance Ombudsman awards on health-insurance claims.
For each award (marked [ID: ...]) return:
- decision: "allowed" (insurer told to pay in full), "partly_allowed" (partial payment or
  ex-gratia), "dismissed" (insurer's decision upheld), or "other" (withdrawn, settled,
  not maintainable, no decision).
- category: the insurer's main ground for rejecting or cutting the claim.
- diagnosis: the illness or treatment, in a few plain words (null if not stated).
- summary: one sentence: what the insurer did, why, and what the Ombudsman decided and why.
Use only what each award says."""


class Label(BaseModel):
    id: str
    decision: str
    category: RejectionCategory
    diagnosis: str | None
    summary: str


class Labels(BaseModel):
    labels: list[Label]


def _call(batch: list[dict]) -> list[Label]:
    body = "\n\n".join(f"[ID: {r['id']}]\n{r['text'][:MAX_CHARS]}" for r in batch)
    for _ in range(20):
        try:
            resp = client().models.generate_content(
                model=get_settings().model_fast,
                contents=[body],
                config=types.GenerateContentConfig(
                    system_instruction=PROMPT,
                    response_mime_type="application/json",
                    response_schema=Labels,
                    temperature=0,
                ),
            )
            return Labels.model_validate_json(resp.text).labels
        except (ClientError, ServerError) as e:
            if getattr(e, "code", None) not in (429, 500, 503):
                raise
            # Trial-project Vertex 429s are intermittent: short jittered retries beat long backoff.
            time.sleep(random.uniform(3, 12))
        except ValueError:  # malformed JSON from the model
            pass
    return []  # skipped; the next run picks these ids up again


def main() -> None:
    rulings = [json.loads(line) for line in (SOURCES / "rulings.jsonl").open(encoding="utf-8")]
    out_path = SOURCES / "rulings_labels.jsonl"
    done = set()
    if out_path.exists():
        done = {json.loads(line)["id"] for line in out_path.open(encoding="utf-8")}
    todo = [r for r in rulings if r["id"] not in done]
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(todo)
    todo = todo[:limit]
    print(f"{len(done)} already labelled, labelling {len(todo)}", flush=True)
    wanted = {r["id"] for r in todo}
    batches = [todo[i : i + BATCH] for i in range(0, len(todo), BATCH)]
    workers = WORKERS
    finished = 0
    with out_path.open("a", encoding="utf-8") as out, ThreadPoolExecutor(workers) as pool:
        for future in as_completed(pool.submit(_call, b) for b in batches):
            for label in future.result():
                if label.id in wanted:
                    out.write(label.model_dump_json() + "\n")
            out.flush()
            finished += 1
            print(f"{finished}/{len(batches)} batches", flush=True)


if __name__ == "__main__":
    main()
