# whirlpool: agent evaluation

Each folder in `cases/` is one claim: the rejection letter and discharge summary (synthetic, fictional names), a pointer to a real public policy wording in `magellan/sources/policies/`, and `case.json` with the answers we expect.

```bash
magellan/ingest/fetch_sources.sh                 # once: downloads the policy PDFs
sombrero/.venv/bin/python whirlpool/run_evals.py # all cases, or pass case ids
```

Scored today (intake agent): document types, insurer, TPA, policy start, admission and first-diagnosis dates, claim amount, currency, rejection code, rejection category, cited clause.

Later: strength verdict (`expected.strength`, strategist) and checker pass rate.

The free AI Studio tier allows 250k input tokens per minute, and each policy is about 50k tokens, so the runner waits and retries on 429 errors. Run before every demo build. Target: 10 cases by week 1, 20 by week 2.
