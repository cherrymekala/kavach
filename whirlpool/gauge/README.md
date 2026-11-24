# whirlpool/gauge: regression gates with agentgauge

`run_evals.py` reports how many fields were right on one run. That's useful, but Gemini doesn't give the same answer every time, even at temperature 0, and a prompt change can raise the token bill without anyone noticing. [agentgauge](https://github.com/cherrymekala/agentgauge) adds what a single pass misses:

- **Repeats.** Every case runs 3 times. A case that passes twice and fails once is flagged as flaky; it isn't counted as a pass.
- **Pipeline order.** `full_agent` records each orchestrator stage as a tool call. The suite fails if a stage goes missing or runs out of order, for example the checker being skipped.
- **Tokens and cost.** `kavach.agents.llm._track` reports Gemini usage to agentgauge during eval runs. In production it does nothing, because agentgauge isn't installed there.
- **A gate.** `agentgauge compare` exits 1 when accuracy drops, cost per case rises by more than 20%, or p95 latency rises by more than 30% against the committed baseline.

The suites are generated from `whirlpool/cases/*/case.json`, so a new case is gated as soon as its folder exists. The field matching is the same as in `run_evals.py`.

## Run

From the repo root, with sombrero's venv, `GOOGLE_API_KEY` in `.env`, and the policy PDFs fetched once (`magellan/ingest/fetch_sources.sh`):

```bash
sombrero/.venv/bin/pip install "agentgauge @ git+https://github.com/cherrymekala/agentgauge"
sombrero/.venv/bin/python whirlpool/gauge/build_suites.py

cd whirlpool/gauge
export GAUGE_PRICE_FAST="<usd per 1M input>,<usd per 1M output>"   # current Gemini prices
export GAUGE_PRICE_REASONING="<in>,<out>"
../../sombrero/.venv/bin/agentgauge run intake.yaml --agent agents:intake_agent --workers 1 \
  --out runs/intake.json --html intake.html

# First time: keep it as the baseline.
cp runs/intake.json baseline-intake.json
# After a prompt or model change:
../../sombrero/.venv/bin/agentgauge compare baseline-intake.json runs/intake.json --html intake.html
```

In CI (`.github/workflows/agent-evals.yml`) the suite runs on Vertex AI with keyless auth. Run `whirlpool/gauge/setup_vertex_ci.sh` once: it creates a service account limited to Vertex AI and a Workload Identity pool that only this repo can use, and it sets the repo variables. Locally, set `USE_VERTEX=true` in `.env` and run `gcloud auth application-default login`. Any run where agents error (quota, auth) now exits with a failure, so a broken run can't become the baseline.

`full.yaml` (with `agents:full_agent`) scores the strength verdict and the stage order. It needs Vertex AI Search, the same as `run_evals.py --full`.

Keep `--workers 1` on the free AI Studio tier: each policy is about 50k tokens, and the agents wait and retry on 429 errors.

## Offline check of the wiring

```bash
sombrero/.venv/bin/python -m pytest whirlpool/gauge -q
```

This replaces Gemini with fakes and checks three things: a perfect run passes, a wrong cited clause on one repeat out of three is reported as flaky, and the pipeline stages are recorded in order.
