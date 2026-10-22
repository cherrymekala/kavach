# Kavach

Multi-agent assistant that helps patients fight health-insurance claim rejections: decode the rejection, build a sourced case, draft the appeal, file with the right dispute body and track it to the end.

Built for AI Builder Cup 2026 on Google Cloud (Gemini, Agent Development Kit, Cloud Run, Firebase).

## Repo map

Each part of the system is named after a galaxy.

| Folder | Galaxy | What it holds | Owner |
|---|---|---|---|
| `andromeda/` | Andromeda, our nearest big neighbour | Web app (PWA) users see | Frontend |
| `sombrero/` | Sombrero, bright core with a wide disc | API and AI agents on Cloud Run | Backend |
| `triangulum/` | Triangulum, small and structural | Terraform for Google Cloud | Infra |
| `magellan/` | Magellanic Clouds, satellites that feed the Milky Way | Country packs, TPA codes, rulings ingestion | Data |
| `whirlpool/` | Whirlpool, everything spirals through it | Evaluation cases and scoring for agent answers | Backend + Data |
| `cartwheel/` | Cartwheel | Architecture notes, API contract, pitch material | Everyone |

## Architecture

```
andromeda (Firebase Hosting)
   │  Firebase Auth token
   ▼
sombrero (Cloud Run, FastAPI + ADK)
   ├── orchestrator ─► intake · code_decoder · policy_rules · strategist
   │                   └─► checker ─► filing ─► escalation
   ├── Firestore (cases)      ├── Cloud Storage (documents)
   ├── Vertex AI Search (rulings)   └── BigQuery (anonymised outcomes)
   ▲
   └── Cloud Scheduler: daily /tracker/tick  ─► WhatsApp deadline reminders

Channels (same pipeline, same cases):
   WhatsApp (Meta Cloud API) ─► /whatsapp/webhook ─┐
   Phone line (Twilio)       ─► /voice/*         ─┼─► accounts.uid_for_phone(number)
                                                   ┘   = the Firebase uid that signed in
magellan ─► country packs (IN, SG, MY) + rulings loaded into Vertex AI Search
```

## Quick start (backend)

```bash
cd sombrero
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # add GOOGLE_API_KEY from AI Studio for local dev
uvicorn kavach.main:app --reload
# http://localhost:8080/docs
```

## Channels

Patients reach Kavach three ways: the web app, a **WhatsApp** chat, and a **phone line**. All
three run the same agents on the same cases. Because sign-in is Firebase phone OTP, the number
someone messages or calls from already identifies their account.

- WhatsApp: `sombrero/src/kavach/routers/whatsapp.py` — send photos/PDFs of the papers, get the
  analysis back, ask questions, download the appeal letter, `DELETE` your data. Deadline
  reminders come from the daily tracker. Setup: `sombrero/README.md`.
- Phone line: `sombrero/src/kavach/routers/voice.py` (Twilio) — case status and a voice hearing
  rehearsal.
- No Meta or Twilio account needed to try the WhatsApp flow locally:
  `python sombrero/scripts/whatsapp_smoke.py`

## Deadlines

| Week | Dates | Checkpoint |
|---|---|---|
| 1 | 30 Sep – 6 Oct | Upload → case summary works through the API |
| 2 | 7 – 13 Oct | Full flow end to end, India + Singapore packs |
| 3 | 14 – 17 Oct | Demo polish, video, proposal. Submit 17 Oct (deadline 18 Oct) |
