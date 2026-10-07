# AGENTS.md — Kavach

Steering notes for any agent (or teammate) working in this repo. Read this before changing code.

## What Kavach is

A multi-agent assistant that helps patients fight health-insurance claim rejections: decode the rejection, build a sourced case, draft the appeal, file it with the right dispute body, and track it to resolution. Built for AI Builder Cup 2026 on Google Cloud (Gemini, ADK, Cloud Run, Firebase). Country = data, not code (add a country by adding one JSON pack).

## Repo map

| Folder | What it is | Touched by |
|---|---|---|
| `sombrero/` | Python backend — FastAPI + Google ADK agents (`src/kavach/`) | backend |
| `andromeda/web/` | **Frontend** — React 19 + TypeScript + Vite (planned; see below) | frontend |
| `magellan/` | Country packs (`packs/IN.json`, `SG.json`, `schema.md`) + ingest scripts | data |
| `whirlpool/` | Eval harness (`run_evals.py`, `cases/*.json`) | backend/data |
| `triangulum/` | Terraform for GCP (`main.tf`, `variables.tf`) | infra |

`andromeda/prototype/`, `cartwheel/`, `*.html`/`*.jpeg` at root, `CLAUDE.md`, `spec.md`, `spec-frontend.md`, `session.md`, `.claude/`, `.agents/` are reference/local only — **never commit**.

## Backend contract (single source of truth)

The API contract is `sombrero/src/kavach/models.py`. It is published as `/openapi.json` on the live API (`https://sombrero-urb5ttky3q-el.a.run.app`). **Any change to `models.py` changes the API** — update the frontend types (`openapi-typescript`) in the same PR and ping the frontend owner.

- Auth: every route (except `/health` and `/tracker/tick`) takes `Authorization: Bearer <Firebase ID token>`; `verify_token` in `sombrero/src/kavach/auth.py`. `AUTH_DISABLED=true` only locally.
- Errors arrive as `{"detail": "..."}` — the text is user-friendly; show it verbatim.
- Routes (17): `POST /cases`, `GET /cases`, `GET/DELETE /cases/{id}`, `DELETE /cases/{id}/documents/{doc_id}`, `POST /cases/{id}/documents`, `POST /cases/{id}/analyse`, `PUT /cases/{id}/complainant`, `POST /cases/{id}/letter`, `GET /cases/{id}/filing`, `GET /cases/{id}/filing.pdf`, `GET /cases/{id}/letter.pdf`, `POST /cases/{id}/filed`, `POST /cases/{id}/reply`, `POST /tracker/tick`, `GET /packs/{country}` (no auth), `GET /health`.
- Case analysis is **async**: `POST /analyse` returns `202`; agents write `case.progress` + `case.status` to Firestore as they run. The UI watches `cases/{id}` with Firestore `onSnapshot` (owners may read their own case per `triangulum/firestore.rules`).

## Frontend (`andromeda/web/`) — build plan

Stack (decided in `spec-frontend.md`): React 19 + TypeScript + Vite · React Router (data routers) · TanStack Query · Firebase JS SDK (Auth phone OTP + Firestore live updates) · Tailwind CSS v4 + **shadcn/ui** (`components.json`, unified `radix-ui`) · i18next · `openapi-typescript`-generated types · `vite-plugin-pwa` · Web Audio API (hearing) · Vitest/Testing Library + Playwright.

Layout:

```
andromeda/web/src/
  api/         client.ts (fetch + token), schema.d.ts (generated), hooks.ts (TanStack Query)
  firebase.ts  Firebase app/auth/firestore init from VITE_FIREBASE_* env
  i18n/        en.json, hi.json, ta.json, te.json, mr.json, zh.json, ms.json
  audio/       recorder worklet + player (16k/24k PCM16 for Gemini Live)
  screens/     start, upload, summary, chances, letter, filing, hearing, tracker, outcome
  components/  Button, Card, SourceChip, Meter, Stepper, Timeline, FileTile…
  styles/tokens.css
```

Screens map 1:1 to the 9-step flow and to API routes — see `spec-frontend.md` §4.

**shadcn/ui notes:** primitives live in `src/components/ui/` (re-exported from `@/components`); our `cn` util is `src/lib/cn.ts`. After `npx shadcn add`, rewrite the emitted `import { cn } from "cn"` → `@/lib/cn` and keep the unified `radix-ui` package (don't install the `cn` package).

### The 9 screens (what we actually build)

1. **Sign in** (`/`) — Firebase phone OTP; language picker first.
2. **Start** (`/start`) — `POST /cases`; country guessed from phone code (+91 → IN, +65 → SG), user can change.
3. **Upload** (`/case/:id/upload`) — `POST /cases/{id}/documents` per file (PDF/JPG/PNG/WEBP/TXT, ≤20 MB, ≤15 files); then `POST /analyse` and watch Firestore `onSnapshot` for live `progress` until `status=ready`.
4. **Summary** (`/case/:id/summary`) — plain-language "what happened": decoded reason, amounts (Indian grouping for INR), timeline, doc labels/warnings.
5. **Chances** (`/case/:id/chances`) — strength meter, sourced arguments (tappable quotes), "won X of Y similar cases", missing-docs checklist, always render `disclaimer`.
6. **Letter** (`/case/:id/letter`) — EN/local toggle, tone chips (`POST /letter {instruction}`), PDF download.
7. **Filing** (`/case/:id/filing`) — `PUT /complainant` form → `GET /filing` fields with `missing` highlighted → `GET /filing.pdf`.
8. **Hearing** (`/case/:id/hearing`) — WebSocket voice rehearsal with Gemini Live + coaching cards + debrief + text fallback.
9. **Tracker** (`/case/:id/tracker`) — `POST /filed`, `POST /reply`, stepper, deadline countdown, event timeline.
10. **Outcome** (`/case/:id/outcome`) — `amount_recovered`, celebration, "download letters/forms now", "Delete my data" (`DELETE /cases/{id}`).

### Channels — what is NOT built now

WhatsApp, Telegram, and a phone voice line are **post-MVP / slides only** (see `spec.md` §2, §5). The prototype shows "WhatsApp"/"Call us" tiles as *coming soon*. The only "connections" we build are: **Firebase Auth (phone OTP) → Kavach REST API → Firestore (read-only) + WebSocket (hearing)**, all served from **Firebase Hosting**. No Twilio/WhatsApp Business/Telegram Bot API work this cycle.

## Skills (installed in `.agents/skills/`, git-ignored)

| Skill | When to use |
|---|---|
| `vercel-react-best-practices` | React/Vite performance, data fetching, bundle size |
| `vercel-composition-patterns` | React 19 component structure, compound components, providers |
| `tailwind-design-system` | Building tokens/components on Tailwind |
| `tailwind-4-docs` | Tailwind **v4** specifics (new config model, `@theme`) |
| `web-design-guidelines` | Accessibility/UI review before shipping a screen |
| `tdd` | Test-first workflow for hooks/components (Vitest) |
| `code-review` | Reviewing PRs, structuring changes |
| `architecture-patterns` | Layering/ports-and-adapters (mostly backend, reference) |
| `architecture-decision-records` | ADR template for big frontend decisions |
| `docker-patterns` | Docker (only if we containerize locally; not required for Firebase Hosting) |
| `frontend-design` (global) | Distinctive visual direction (typography, color, spacing) |

Multi-agent (Google ADK / Agents SDK) skills are **backend's** concern (Sharan owns `sombrero/`); the frontend consumes the API, it does not build agents.

## Frontend build phases & parallel-session rules

The 9 screens split into **phases**. Each phase owns exactly one `src/screens/<name>/` folder and is code-independent (it reads the case id from `useParams()` and uses the frozen API hooks). This is what makes parallel work safe.

### Frozen shared files — DO NOT edit in a phase session

`src/styles/globals.css` · `src/lib/theme.tsx` · `src/lib/cn.ts` · `src/lib/{money,dates,download}.ts` · `src/components/ui/*` · `src/components/*` (feature components) · `src/components/index.ts` · `src/firebase.ts` · `src/auth.tsx` · `src/api/{client,schema,types,hooks,live}.*` · `src/main.tsx` · `src/App.tsx` · `src/router.tsx` · `package.json` · `components.json` · `.oxlintrc.json` · `tsconfig*`.

If a phase needs a shared change (a new primitive, a new hook, a route, a dependency), **stop and do it as a separate coordinated PR** — never silently edit shared files.

### Phases (own only the "Files you own" column)

| Phase | Screen | Route | Files you own | API |
|---|---|---|---|---|
| 1 | Start | `/start` | `src/screens/start/` | `POST /cases` |
| 2 | Upload + Analysing | `/case/:id/upload` | `src/screens/upload/` | `POST /documents`, `POST /analyse`, `useLiveCase` |
| 3 | Summary | `/case/:id/summary` | `src/screens/summary/` | `GET /cases/{id}` → `facts` |
| 4 | Chances | `/case/:id/chances` | `src/screens/chances/` | `assessment` |
| 5 | Letter | `/case/:id/letter` | `src/screens/letter/` | `POST /letter`, `GET /letter.pdf` |
| 6 | Filing | `/case/:id/filing` | `src/screens/filing/` | `PUT /complainant`, `GET /filing`, `GET /filing.pdf` |
| 7 | Hearing | `/case/:id/hearing` | `src/screens/hearing/`, `src/audio/` | WebSocket |
| 8 | Tracker | `/case/:id/tracker` | `src/screens/tracker/` | `POST /filed`, `POST /reply` |
| 9 | Outcome | `/case/:id/outcome` | `src/screens/outcome/` | `DELETE /cases/{id}` |
| 10 | Polish | — | `src/i18n/`, e2e, PWA, empty/error states | — |

**Rules for every phase session:**
1. Edit only your phase's files. Phase-local components live **inside** your screen folder (e.g. `src/screens/chances/SourceSheet.tsx`), imported directly — do **not** touch `components/index.ts`.
2. Read data via the frozen hooks (`useCase(id)`, `useLiveCase(id)`, `useFiling(id, step)`…) and primitives from `@/components/ui/…`. PDFs: `apiBlob` + `downloadBlob`.
3. Import components directly (`@/components/ui/button`) or from `@/components` (barrel is frozen and complete).
4. Commit per screen, repo style ("Added the X screen"), on a branch `feat/<phase>`.
5. Run `npm run build` and `npm run lint` before committing.

### How to run phases (pick one)

- **Sequential (recommended if new to git):** do one phase at a time, commit, move on. The order 1→9 follows the demo path; 10 last.
- **Parallel:** one branch per phase. If sessions share one machine, use **git worktrees** so each session has its own directory and branch (never two sessions `git add`/`commit` in the same worktree):
  ```bash
  git worktree add ../kavach-phase3 -b feat/summary main
  ```
  Each session works in its own directory and only its own files. Merge via PRs.

To see what other sessions are doing: `git branch -a` + `gh pr list`.

## Commands

Backend (from `sombrero/`):
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
uvicorn kavach.main:app --reload      # http://localhost:8080/docs
pytest                                 # 24 tests
ruff check . && ruff format .
```

Frontend (from `andromeda/web/`, once scaffolded):
```bash
npm install
npm run dev                            # Vite dev server
npm run build && firebase deploy --only hosting
npm run test                           # Vitest
npx openapi-typescript https://sombrero-urb5ttky3q-el.a.run.app/openapi.json -o src/api/schema.d.ts
```

## Rules

- Never commit `.env`, secrets, service-account JSON, prototypes, references, docs, `CLAUDE.md`, `spec*.md`, `session.md`, `.claude/`, `.agents/`.
- Model IDs live in `.env` / cloudbuild substitutions, never hard-coded.
- Backend `.env` is read from the **repo root** (`config.py` reads `REPO_ROOT/.env`), not `sombrero/`.
- Frontend env vars are `VITE_*` only (`VITE_API_URL`, `VITE_FIREBASE_*`).
- Keep the UI honest: every argument must show its source; always render `assessment.disclaimer`.

## Git & commits (frontend owner is new to PRs — always steer here)

When the user says "commit" or "push", **do not just run `git add -A`**. Do this instead, in order, and say what you're doing:

1. `git status` + `git diff` first — show the user what changed and confirm only intended files are staged.
2. **Never stage** (already git-ignored, but double-check): `.env`, `.venv/`, `*.egg-info/`, `__pycache__/`, `CLAUDE.md`, `spec.md`, `spec-frontend.md`, `session.md`, `.claude/`, `.agents/`, `skills-lock.json`, `Kavach_Prototype.html`, `arch_health.jpeg`, `andromeda/prototype/`, `cartwheel/`.
3. Commit only the frontend + docs: `andromeda/web/**`, `AGENTS.md`, `.gitignore`.
4. Work on a **feature branch** off `main`, never push straight to `main` — `main` triggers a Cloud Build deploy.
5. Open a **PR** (use `gh pr create`) with a clear title/description; `main` = `git log --oneline -5` to match repo commit style (short, imperative, e.g. "Add X").
6. If `models.py`/`/openapi.json` changed upstream, regenerate `src/api/schema.d.ts` **in the same PR** and flag the backend owner.
7. Never force-push, never amend pushed commits, never skip hooks.

If anything looks off (a secret, a large binary, a stray prototype file), **stop and ask** before committing.

## Reference

- `spec.md` — overall project spec, requirements, status log (local).
- `spec-frontend.md` — full frontend spec: screens→API table, hearing WebSocket protocol, design tokens, milestones, acceptance criteria (local).
- Live API docs: `https://sombrero-urb5ttky3q-el.a.run.app/docs`