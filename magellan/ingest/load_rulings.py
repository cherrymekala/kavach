"""Load labelled rulings into the Vertex AI Search data store (embeddings are built by the service).

Reads magellan/sources/rulings.jsonl + rulings_labels.jsonl. Rulings without a label are skipped.
Run from the repo root after `terraform apply`:
    sombrero/.venv/bin/python magellan/ingest/load_rulings.py
"""

import json
from pathlib import Path

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as de

from kavach.config import get_settings

SOURCES = Path(__file__).resolve().parents[1] / "sources"
BATCH = 100  # import_documents inline limit

# indexable = usable in filters; searchable = matched by keyword/semantic query.
SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "country": {"type": "string", "retrievable": True, "indexable": True},
        "insurer": {"type": "string", "retrievable": True, "indexable": True, "searchable": True},
        "decision": {"type": "string", "retrievable": True, "indexable": True},
        "category": {"type": "string", "retrievable": True, "indexable": True},
        "award_date": {"type": "string", "retrievable": True, "indexable": True},
        "diagnosis": {"type": "string", "retrievable": True, "searchable": True},
        "summary": {"type": "string", "retrievable": True, "searchable": True},
        "case_no": {"type": "string", "retrievable": True},
        "source": {"type": "string", "retrievable": True},
    },
}


def _records() -> list[dict]:
    labels = {}
    for line in (SOURCES / "rulings_labels.jsonl").open(encoding="utf-8"):
        label = json.loads(line)
        labels[label["id"]] = label
    out = []
    for line in (SOURCES / "rulings.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        label = labels.get(r["id"])
        if label and label["decision"] != "other":
            out.append(
                {**r, **{k: label[k] for k in ("decision", "category", "diagnosis", "summary")}}
            )
    return out


def import_records(records: list[dict], update_schema: bool = True) -> None:
    """Upsert rulings (INCREMENTAL keeps every other document in the data store)."""
    s = get_settings()
    if not s.rulings_engine:
        raise SystemExit("Set RULINGS_ENGINE in .env")
    opts = ClientOptions(quota_project_id=s.gcp_project)
    store = f"projects/{s.gcp_project}/locations/global/collections/default_collection/dataStores/{s.rulings_engine}"
    if update_schema:
        de.SchemaServiceClient(client_options=opts).update_schema(
            request=de.UpdateSchemaRequest(
                schema=de.Schema(
                    name=f"{store}/schemas/default_schema", json_schema=json.dumps(SCHEMA)
                )
            )
        ).result(timeout=600)
        print("schema updated")

    docs_client = de.DocumentServiceClient(client_options=opts)
    branch = f"{store}/branches/default_branch"
    for i in range(0, len(records), BATCH):
        docs = [
            de.Document(
                id=r["id"],
                struct_data={k: r[k] for k in SCHEMA["properties"] if r.get(k) is not None},
                content=de.Document.Content(
                    mime_type="text/plain", raw_bytes=r["text"].encode("utf-8")
                ),
            )
            for r in records[i : i + BATCH]
        ]
        op = docs_client.import_documents(
            request=de.ImportDocumentsRequest(
                parent=branch,
                inline_source=de.ImportDocumentsRequest.InlineSource(documents=docs),
                reconciliation_mode=de.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
            )
        )
        result = op.result(timeout=900)
        errors = len(result.error_samples)
        print(
            f"{min(i + BATCH, len(records))}/{len(records)} imported"
            + (f", {errors} errors: {result.error_samples[0].message}" if errors else "")
        )


def main() -> None:
    import_records(_records())


if __name__ == "__main__":
    main()
