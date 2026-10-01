# sombrero: API and agents

FastAPI app plus Google ADK agents, deployed as one Cloud Run service.

```
src/kavach/
  main.py          FastAPI app and routers
  config.py        settings from env
  auth.py          Firebase token check
  models.py        case, document and argument schemas (shared API contract)
  routers/         cases, documents, analysis, tracker
  agents/          orchestrator + one module per specialist agent
  tools/           Firestore, Cloud Storage, Vertex AI Search, country packs
packs/             country packs copied from ../magellan at build time
```

Run locally: see the root README. Tests: `pytest`.
