# magellan: country packs and data

- `packs/IN.json`, `packs/SG.json`: rules, dispute steps, forms, deadlines, rejection codes. Copied into `sombrero/packs` at build time.
- `rulings/raw/`: Ombudsman awards and FIDReC case studies as downloaded (not committed if large).
- `ingest/`: scripts that clean rulings and load them into Vertex AI Search.

Sample values below are placeholders. Replace them with checked data before the demo, and never commit real patient documents.
