"""Label rulings with a Vertex AI Gemini batch job: no rate limits, half price, runs server-side.

    sombrero/.venv/bin/python magellan/ingest/label_rulings_batch.py submit   # upload + start
    sombrero/.venv/bin/python magellan/ingest/label_rulings_batch.py status
    sombrero/.venv/bin/python magellan/ingest/label_rulings_batch.py collect  # merge into rulings_labels.jsonl

Only ids missing from rulings_labels.jsonl are sent. Uses USE_VERTEX regardless of .env.
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ["USE_VERTEX"] = "true"

from google.cloud import storage
from google.genai import types
from label_rulings import MAX_CHARS, PROMPT, Label

from kavach.agents.llm import client
from kavach.config import get_settings
from kavach.models import RejectionCategory

SOURCES = Path(__file__).resolve().parents[1] / "sources"
LABELS = SOURCES / "rulings_labels.jsonl"
JOB_FILE = SOURCES / "batch_job.json"

SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "id": {"type": "STRING"},
        "decision": {"type": "STRING", "enum": ["allowed", "partly_allowed", "dismissed", "other"]},
        "category": {"type": "STRING", "enum": [c.value for c in RejectionCategory]},
        "diagnosis": {"type": "STRING", "nullable": True},
        "summary": {"type": "STRING"},
    },
    "required": ["id", "decision", "category", "summary"],
}


def _labelled() -> set[str]:
    if not LABELS.exists():
        return set()
    return {json.loads(line)["id"] for line in LABELS.open(encoding="utf-8")}


def submit() -> None:
    s = get_settings()
    done = _labelled()
    todo = [json.loads(line) for line in (SOURCES / "rulings.jsonl").open(encoding="utf-8")]
    todo = [r for r in todo if r["id"] not in done]
    lines = []
    for r in todo:
        lines.append(json.dumps({
            "request": {
                "systemInstruction": {"parts": [{"text": PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": f"[ID: {r['id']}]\n{r['text'][:MAX_CHARS]}"}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": SCHEMA},
            }
        }, ensure_ascii=False))
    prefix = f"batch/labels-{time.strftime('%Y%m%d-%H%M%S')}"
    bucket = storage.Client(project=s.gcp_project).bucket(s.docs_bucket)
    bucket.blob(f"{prefix}/input.jsonl").upload_from_string("\n".join(lines) + "\n", content_type="application/jsonl")
    job = client().batches.create(
        model=s.model_fast,
        src=f"gs://{s.docs_bucket}/{prefix}/input.jsonl",
        config=types.CreateBatchJobConfig(dest=f"gs://{s.docs_bucket}/{prefix}/output"),
    )
    JOB_FILE.write_text(json.dumps({"name": job.name, "prefix": prefix, "requests": len(lines)}))
    print(f"submitted {len(lines)} requests: {job.name} ({job.state})")


def status() -> types.BatchJob:
    job = client().batches.get(name=json.loads(JOB_FILE.read_text())["name"])
    print(job.state, job.completion_stats or "")
    return job


def collect() -> None:
    s = get_settings()
    info = json.loads(JOB_FILE.read_text())
    job = status()
    if job.state != types.JobState.JOB_STATE_SUCCEEDED:
        raise SystemExit("job not finished yet")
    done = _labelled()
    added = failed = 0
    bucket = storage.Client(project=s.gcp_project).bucket(s.docs_bucket)
    with LABELS.open("a", encoding="utf-8") as out:
        for blob in bucket.list_blobs(prefix=f"{info['prefix']}/output"):
            if not blob.name.endswith(".jsonl"):
                continue
            for line in blob.download_as_text().splitlines():
                try:
                    row = json.loads(line)
                    text = row["response"]["candidates"][0]["content"]["parts"][0]["text"]
                    label = Label.model_validate_json(text)
                except (KeyError, IndexError, ValueError):
                    failed += 1
                    continue
                if label.id not in done:
                    done.add(label.id)
                    out.write(label.model_dump_json() + "\n")
                    added += 1
    print(f"added {added} labels, {failed} failed rows; total labelled {len(done)}")


if __name__ == "__main__":
    {"submit": submit, "status": status, "collect": collect}[sys.argv[1] if len(sys.argv) > 1 else "status"]()
