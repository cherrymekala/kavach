# Setting Kavach up

Four stages. Each one ends with a check you can run, so you know it worked before moving on.

| Stage | Time | Needs |
|---|---|---|
| [1. Locally](#1-locally-5-minutes) | 5 min | nothing |
| [2. Deployed](#2-deployed) | 20 min | `gcloud`, `terraform`, a GCP project |
| [3. WhatsApp](#3-whatsapp) | 15 min | a Meta Business app |
| [4. Payments](#4-payments) | 15 min | Razorpay + Stripe accounts |

---

## 1. Locally (5 minutes)

### Backend

```bash
cd <repo>
cp sombrero/.env.example .env      # NOTE: the repo ROOT, not sombrero/
```

`config.py` reads `.env` from the repo root. Putting it in `sombrero/` is the single most common
setup mistake — the app starts and silently ignores every setting.

Open `.env` and set `GOOGLE_API_KEY` (a free AI Studio key is enough). Leave `AUTH_DISABLED=true`:
that switches cases to memory and uploads to `./.uploads`, so no Firebase or GCS is needed.

```bash
cd sombrero
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
uvicorn kavach.main:app --reload
```

**Check:** <http://localhost:8080/docs> loads, and:

```bash
curl -s localhost:8080/health          # {"ok":true}
curl -s localhost:8080/packs/IN | head -c 120
```

### Frontend

```bash
cd andromeda/web
cp .env.example .env
# set VITE_API_URL=http://localhost:8080
pnpm install && pnpm dev
```

**Check:** <http://localhost:5173> renders.

> **Sign-in does not work locally**, by design. Phone OTP needs real Firebase config, and without
> it every API call fails with "Firebase is not configured". Use the fixture-backed preview routes
> instead — they need no sign-in:
> `/preview/case/demo/summary`, `/preview/case/demo/chances`, `/preview/unlock/IN/demo`

### Tests

```bash
pytest sombrero/tests -q              # 125 backend tests
cd andromeda/web && pnpm test         # 8 frontend tests
```

The same commands run in CI (`.github/workflows/ci.yml`) on every pull request, along with
`ruff check` and `pnpm build`. `conftest.py` points `PACKS_DIR` at `magellan/packs`, so the suite
runs from any directory.

---

## 2. Deployed

```bash
cd triangulum
cp terraform.tfvars.example terraform.tfvars    # project_id, billing_account, region
terraform init && terraform apply
```

### Then create the secrets — **before** you deploy

`cloudbuild.yaml` tells Cloud Run to mount **eight** secrets. If any of them has no version, the
Cloud Run step fails and the deploy stops. Create them all first:

```bash
printf %s "$TWILIO_ACCOUNT_SID" | gcloud secrets versions add twilio-account-sid    --data-file=-
printf %s "$TWILIO_AUTH_TOKEN"  | gcloud secrets versions add twilio-auth-token     --data-file=-
printf %s "$WHATSAPP_ACCESS_TOKEN" | gcloud secrets versions add whatsapp-access-token --data-file=-
printf %s "$WHATSAPP_APP_SECRET"   | gcloud secrets versions add whatsapp-app-secret   --data-file=-
printf %s "$RAZORPAY_KEY_ID"     | gcloud secrets versions add razorpay-key-id      --data-file=-
printf %s "$RAZORPAY_KEY_SECRET" | gcloud secrets versions add razorpay-key-secret  --data-file=-
printf %s "$STRIPE_SECRET_KEY"   | gcloud secrets versions add stripe-secret-key    --data-file=-
printf %s "$STRIPE_WEBHOOK_SECRET" | gcloud secrets versions add stripe-webhook-secret --data-file=-
```

A secret with **no version** counts as missing. An empty *value* is worse: it turns a signature
check into a rubber stamp (see `AGENTS.md`), which is why the code now refuses when a signing
secret is empty.

Then set the non-secret values in `cloudbuild.yaml` substitutions and push to `main`:

| Substitution | Value |
|---|---|
| `_WHATSAPP_PHONE_NUMBER_ID` | from Meta (stage 3) |
| `_WHATSAPP_VERIFY_TOKEN` | any random string — paste the same into Meta |
| `_WHATSAPP_TEMPLATE` | leave empty until a template is approved |
| `_PAYMENTS_ENABLED` | `false` until stage 4 |

**Check:** `curl -s https://<service>.run.app/health` → `{"ok":true}`.

---

## 3. WhatsApp

1. developers.facebook.com → **Create app** → type **Business** → add product **WhatsApp**.
2. **WhatsApp → API Setup** → add your number under **"To"** and verify the code Meta sends.
   A test number can only message numbers on that list.
3. Copy the **Phone number ID** (not the `+1 555…` display number).
4. **Permanent token:** business.facebook.com → Business settings → **System users** → create one →
   **Assign assets** (your app *and* the WhatsApp account) → **Generate token** with
   `whatsapp_business_messaging`. The API Setup token expires within hours and cannot back a webhook.
5. **App secret:** App settings → Basic → App secret (32 hex characters).

Put all of it in the repo-root `.env`:

```bash
WHATSAPP_PHONE_NUMBER_ID=…
WHATSAPP_ACCESS_TOKEN=…
WHATSAPP_APP_SECRET=…
WHATSAPP_VERIFY_TOKEN=<random>
WHATSAPP_DRY_RUN=false          # true logs instead of sending
```

Point Meta's webhook at `https://<service>.run.app/whatsapp/webhook`, paste the same verify token,
and subscribe to the **messages** field — in the dashboard, or from the command line (below).

#### Register the webhook without the dashboard

The dashboard needs a publicly reachable URL first, which makes local development awkward. The
same subscription can be created over the Graph API with an **app access token**, and Meta calls
your endpoint to verify it as part of the request:

```python
httpx.post("https://graph.facebook.com/v21.0/<APP_ID>/subscriptions", data={
    "object": "whatsapp_business_account",
    "callback_url": "https://<your-public-url>/whatsapp/webhook",
    "verify_token": "<WHATSAPP_VERIFY_TOKEN>",
    "fields": "messages",
    "access_token": "<APP_ID>|<WHATSAPP_APP_SECRET>",
})
# -> {"success": true}   and GET /<APP_ID>/subscriptions shows "active": true
```

For local work, expose port 8080 with any HTTPS tunnel, e.g.:

```bash
ssh -R 80:localhost:8080 nokey@localhost.run   # prints https://<random>.lhr.life
```

A quick-tunnel URL changes when it restarts, so re-run the subscription call with the new URL.
The tunnel only exists while it runs — for anything permanent, deploy and register the Cloud Run
URL instead.

**Verify, in this order:**

```bash
python sombrero/scripts/whatsapp_check.py                    # shapes
python sombrero/scripts/whatsapp_check.py --live             # does Meta accept the token?
python sombrero/scripts/whatsapp_check.py --webhook https://<service>.run.app
python sombrero/scripts/whatsapp_check.py --live --send +919493925966
```

The webhook step also proves a **forged** signature is rejected — before that check passes, assume
anyone can post to your endpoint.

### Trying it with no Meta account

The whole conversation runs locally, logging every outbound message instead of sending it:

```bash
python sombrero/scripts/whatsapp_smoke.py
```

Or against a running server (what I used to verify this):

```bash
WHATSAPP_APP_SECRET=local-test-app-secret WHATSAPP_DRY_RUN=true \
  uvicorn kavach.main:app --port 8080
# then POST a body signed with sha256=HMAC(secret, body) to /whatsapp/webhook
```

Dry-run messages are logged at **WARNING** level, so they appear in a default `uvicorn` run.

---

## 4. Payments

Fares: ₹399 / S$39 / RM99, one-time per case, for the letter + form PDFs + hearing rehearsal.

```bash
PAYMENTS_ENABLED=true
RAZORPAY_KEY_ID=…          # India, test mode
RAZORPAY_KEY_SECRET=…
STRIPE_SECRET_KEY=…        # Singapore, Malaysia, test mode
STRIPE_WEBHOOK_SECRET=whsec_…
APP_URL=https://kavach-510312.web.app   # where Stripe sends the patient back
```

Then in Stripe → Developers → Webhooks, add `https://<service>.run.app/payments/stripe/webhook`
for `checkout.session.completed`; the signing secret it shows is `STRIPE_WEBHOOK_SECRET`.

To test the webhook without deploying:

```bash
stripe listen --forward-to localhost:8080/payments/stripe/webhook
```

**Check:** `curl -s localhost:8080/packs/IN` shows a `price_amount` only when payments are on, and
`GET /cases/<id>/letter.pdf` returns **402** until the case is paid.

Never enable payments with a signing secret missing or empty — the endpoints refuse rather than
trust the caller, but a misconfigured secret means nobody can pay at all.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| Settings seem ignored | `.env` is in `sombrero/` instead of the repo root |
| `FileNotFoundError: packs/IN.json` | run from the repo root with `PACKS_DIR=magellan/packs` |
| Every API call: "Firebase is not configured" | no `VITE_FIREBASE_*`, and sign-in needs them — use preview routes locally |
| Meta webhook verification fails | the deployed `WHATSAPP_VERIFY_TOKEN` differs; `whatsapp_check.py --webhook` says which side |
| Cloud Run deploy fails on secrets | a secret has no version (stage 2) |
| `401` on every route in prod | `AUTH_DISABLED` must be **false** there |
| WhatsApp replies never arrive | outside Meta's 24-hour window without `WHATSAPP_TEMPLATE`, they are logged and skipped |
| Send fails `131030` | the recipient is not on the test number's allow list (API Setup → To → Manage phone number list) |
| Send fails `131047` | token and phone number ID are fine; Meta wants the patient to message first |
