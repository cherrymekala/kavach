# Kavach

An AI assistant that helps patients fight health-insurance claim rejections. It decodes the insurer's reason, builds a case from the patient's own papers and the published rules, drafts the appeal, prepares the official complaint form and tracks the deadlines until the claim is settled.

Works in **India, Singapore and Malaysia**, in English plus several local languages. Built for the AI Builder Cup 2026 on Google Cloud (Gemini, Cloud Run, Firebase).

## What it does

- **Decodes the rejection.** Reads the rejection letter, maps the insurer's code to the official list, and explains it in plain words.
- **Builds a sourced case.** Every argument quotes the policy clause, the regulation or a past Ombudsman ruling. A checker removes any claim whose quote doesn't appear in its source.
- **Drafts the appeal.** A letter in English or the patient's language, with tone changes ("firmer", "shorter").
- **Prepares the filing.** Official forms for the Insurance Ombudsman (India), FIDReC (Singapore) and FMOS (Malaysia), with the right office chosen from the patient's address.
- **Tracks the case.** Deadlines, reminders, and the next step. A daily job checks every open case.
- **Checks before discharge.** Before the patient leaves hospital, flags what the insurer is likely to cut, with a fix for each item.
- **Rehearses the hearing.** A voice practice session with a live Ombudsman and insurer representative, with coaching after each answer.
- **Shows the patterns.** Public report of how disputes ended, by ground, insurer and year.

## Channels

Same agents, same cases, three ways in:

| Channel | Status | Where |
|---|---|---|
| Web app (PWA) | live | `andromeda/web` |
| WhatsApp (Meta Cloud API) | live | `sombrero/src/kavach/routers/whatsapp.py` |
| Phone line (Twilio) | built, switched off until a paid Twilio account exists | `sombrero/src/kavach/routers/voice.py` |

Sign-in is Firebase phone OTP, so the number someone writes from already identifies their account.

Payments (the appeal pack, ₹399 / S$39 / RM99) are built and switchable with `PAYMENTS_ENABLED`. Off by default.

## Repo map

Each part of the system is named after a galaxy.

| Folder | Galaxy | What it holds | Owner |
|---|---|---|---|
| `andromeda/` | Andromeda | Web app (React, Vite, Tailwind), installable PWA | Frontend |
| `sombrero/` | Sombrero | API and agents (FastAPI, Gemini, runs on Cloud Run) | Backend |
| `triangulum/` | Triangulum | Terraform for Google Cloud, Firebase and secrets | Infra |
| `magellan/` | Magellanic Clouds | Country packs (IN, SG, MY), rulings, regulation text, ingest scripts | Data |
| `whirlpool/` | Whirlpool | Evaluation cases and scoring for the agents | Backend + Data |
| `cartwheel/` | Cartwheel | Architecture notes and pitch material (not in git) | Everyone |

## Architecture

```
andromeda (Firebase Hosting)  ──► Firebase Auth token
WhatsApp (Meta Cloud API)     ──► /whatsapp/webhook ─┐
Phone line (Twilio, parked)   ──► /voice/*          ─┤
                                                     ▼
sombrero (Cloud Run, FastAPI)
   orchestrator ─► intake ─► code_decoder ─► policy_rules ─► strategist ─► checker
                    └─► filing (letter, form) ─► escalation (tracker)
   ├── Firestore (cases, quotas)      ├── Cloud Storage (uploads, 30 days after resolution)
   ├── Vertex AI Search (rulings)     └── Secret Manager (API keys)
   └── Cloud Scheduler: daily /tracker/tick (deadlines, reminders)

magellan ─► country packs (IN, SG, MY) and rulings loaded into Vertex AI Search
```

Models (set in `cloudbuild.yaml` and `.env`, never hard-coded):
- `gemini-3.5-flash-lite` for intake, extraction and classification
- `gemini-3.8-flash` for strategy, drafting, coaching
- `gemini-live-2.5-flash-native-audio` for the hearing and phone voice

## Quick start

Full setup, with a check at each stage, is in **[SETUP.md](SETUP.md)**. The short version:

```bash
cp sombrero/.env.example .env          # the .env lives in the repo ROOT
# set GOOGLE_API_KEY (a free AI Studio key is enough); leave AUTH_DISABLED=true locally

cd sombrero
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn kavach.main:app --reload       # http://localhost:8000/docs
```

Frontend:

```bash
cd andromeda/web
pnpm install
pnpm dev                               # http://localhost:5173
```

## Tests

```bash
cd sombrero && pytest                  # backend (about 125 tests)
cd andromeda/web && pnpm test          # frontend
python whirlpool/run_evals.py          # intake accuracy on the sample cases
python whirlpool/run_evals.py --full   # full pipeline: strength verdicts
python whirlpool/run_evals.py --discharge
```

The evals call the live models, so they need credentials and take a few minutes.

## Deploy

Pushing to `main` runs `cloudbuild.yaml`, which builds `sombrero/` and deploys it to Cloud Run in `asia-south1`. The frontend deploys to Firebase Hosting.

Before a deploy, every secret that `cloudbuild.yaml` mounts needs an enabled version in Secret Manager. A missing one fails the deploy. The list and the steps are in `SETUP.md`.

Feature switches live in `cloudbuild.yaml` (`_PAYMENTS_ENABLED`) and the trigger's substitutions (`_WHATSAPP_PHONE_NUMBER_ID`).

## Documentation

- [`SETUP.md`](SETUP.md): local setup, deploy, WhatsApp, payments, each with a check
- [`sombrero/README.md`](sombrero/README.md): backend details and scripts
- [`spec.md`](spec.md), [`spec-frontend.md`](spec-frontend.md): product and frontend specs (local notes)

## Important

Kavach gives information, not legal advice. Every output says so, and the patient must check each document before they sign or send it. Use demo data only when testing: the app records whatever it is given.
