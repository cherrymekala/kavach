# magellan: country packs and data

- `packs/IN.json`, `packs/SG.json`: rules, dispute steps, forms, deadlines, rejection codes. Single source of truth: copied into the image at build time; local dev reads them via `PACKS_DIR=magellan/packs`.
- `sources/` (git-ignored; public documents that contain real names): Ombudsman award books, policy wordings, IRDAI circular, NHCX codes, recent High Court judgments.
- `ingest/`: the data pipeline.

## Rulings pipeline

```bash
magellan/ingest/fetch_sources.sh                          # 1. download PDFs (~50 MB)
python3 magellan/ingest/split_awards.py                   # 2. books -> sources/rulings.jsonl (~3,250 awards)
USE_VERTEX=true \
  sombrero/.venv/bin/python magellan/ingest/label_rulings.py   # 3. Gemini labels: decision, category, diagnosis, summary
sombrero/.venv/bin/python magellan/ingest/load_rulings.py      # 4. import into Vertex AI Search (needs terraform apply)
python3 magellan/ingest/build_in_regulations.py              # regulations outline -> packs/IN.json
python3 magellan/ingest/build_in_ombudsman_offices.py        # 18 current Ombudsman offices -> packs/IN.json
```

## Singapore pack

```bash
python3 magellan/ingest/build_sg_pack.py                     # MAS / MOH / FIDReC rules (verbatim) + FIDReC ladder -> packs/SG.json
python3 magellan/ingest/fetch_fidrec.py                      # FIDReC case studies -> sources/sg/fidrec
cd magellan/ingest && USE_VERTEX=true PYTHONPATH=. ../../sombrero/.venv/bin/python load_fidrec.py   # label + load (country SG)
```

FIDReC publishes only ~40 anonymised case studies (14 insurance), so Singapore precedent search is thin by design.

Step 3 is resumable and costs well under $1 on Vertex; the free AI Studio tier is too slow (~7 h).
Vertex AI Search builds the embeddings itself; it runs in `global` (the only APAC-usable option), so it holds public rulings only.

Never commit real patient documents.
