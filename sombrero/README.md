# sombrero: API and agents

FastAPI app plus Google ADK agents, deployed as one Cloud Run service.

```
src/kavach/
  main.py          FastAPI app and routers
  config.py        settings from env
  auth.py          Firebase token check
  models.py        case, document and argument schemas (shared API contract)
  routers/         cases, documents, analysis, tracker, hearing, voice, whatsapp
  agents/          orchestrator + one module per specialist agent
  tools/           Firestore, Cloud Storage, Vertex AI Search, country packs
packs/             country packs copied from ../magellan at build time
```

## Channels

Three ways in, one pipeline behind them:

| Channel | Transport | Identified by |
|---|---|---|
| Web app | REST + WebSocket | Firebase ID token |
| Phone line | Twilio webhooks + media stream | the caller's number |
| WhatsApp | Meta Cloud API webhooks | the sender's number |

Because sign-in is Firebase phone OTP, the number someone calls or messages from already maps to
their uid and their cases — there is no separate linking step (`tools/accounts.py`).

### WhatsApp setup

Do these in order, running the checker after each step — it names the setting that is wrong
instead of leaving you to guess:

```bash
# 1. Are the values present, and the right shape? (no network needed)
python sombrero/scripts/whatsapp_check.py
# 2. Does Meta accept the token and the phone number id?
python sombrero/scripts/whatsapp_check.py --live
# 3. Does the deployed service hold the same verify token and app secret?
python sombrero/scripts/whatsapp_check.py --webhook https://<your-service>.run.app
# 4. Send a real message, to prove the whole path
python sombrero/scripts/whatsapp_check.py --live --send +91xxxxxxxxxx
```

1. At developers.facebook.com create a **Business** app and add the **WhatsApp** product. This
   creates the test number and a WhatsApp Business Account.
2. WhatsApp → API Setup: add the patient's mobile as a recipient and verify it with Meta's code.
   A test number can only message recipients on that list.
3. Create a **permanent** access token from a Business **system user** holding the
   `whatsapp_business_messaging` permission. Temporary tokens expire within hours and cannot back
   a webhook.
4. Put the values in the repo-root `.env` (see `.env.example`): `WHATSAPP_PHONE_NUMBER_ID`,
   `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`.
5. In Meta's webhook setup point the callback at `https://<host>/whatsapp/webhook`, paste the same
   `WHATSAPP_VERIFY_TOKEN`, and subscribe to the **messages** field. Meta verifies the URL with a
   GET challenge, which the app answers.
6. Deployed, the two secrets come from Secret Manager (`triangulum/main.tf`) and are injected by
   `cloudbuild.yaml`; the phone number id and verify token ride along as plain env vars
   (`_WHATSAPP_PHONE_NUMBER_ID`, `_WHATSAPP_VERIFY_TOKEN`).
7. Set `VITE_WHATSAPP_NUMBER` for the web app so the account menu can offer the same channel.

Optional: `WHATSAPP_TEMPLATE`. Meta only allows free-form messages within 24 hours of the
patient's last message, so deadline reminders sent after that need a template approved in Meta
Business Manager. Set its name here and the daily tracker will use it; without it those reminders
are logged and skipped rather than dropped silently.

The redelivery markers in the `seen` collection are cleared by a Firestore TTL policy
(`google_firestore_field.seen_ttl`), so nothing grows without bound.

Exercise the conversation itself with no credentials and no network:

```bash
python sombrero/scripts/whatsapp_smoke.py    # from the repo root
```

Run locally: see the root README. Tests: `pytest` (from the repo root, with
`PACKS_DIR=magellan/packs`).
