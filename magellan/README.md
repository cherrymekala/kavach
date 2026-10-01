# magellan: country packs and data

- `packs/IN.json`, `packs/SG.json`: rules, dispute steps, forms, deadlines, rejection codes. Single source of truth: copied into the image at build time; local dev reads them via `PACKS_DIR=../magellan/packs`.
- `rulings/raw/`: Ombudsman awards and FIDReC case studies as downloaded (not committed if large).
- `ingest/`: scripts that clean rulings and load them into Vertex AI Search.

Sample values below are placeholders. Replace them with checked data before the demo, and never commit real patient documents.
