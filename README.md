# Meeting-to-Actions

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Paste a meeting transcript → get a conflict-free task list with owners, deadlines and priorities, plus a ready-to-send follow-up email for each person.** Built on NVIDIA Nemotron models served by Nebius Token Factory.

> Track: **Best Apps & Agents** · Nebius × NVIDIA Hackathon 2026

- **Demo:** https://meeting-to-actions.onrender.com (free hosting: if it's been idle, the first load takes ~1 minute to wake up)
- **Video:** https://www.youtube.com/watch?v=mNIgZXrIAU0

---

## Why

Meetings end with a pile of half-made commitments: tasks get reassigned mid-call, deadlines clash, and nobody sends the follow-up. Meeting-to-Actions turns the raw transcript into a plan people can act on, and resolves the contradictions a simple summariser would miss.

## How it uses NVIDIA Nemotron — tiered routing

Each step goes to the smallest Nemotron model that can do it well:

| Step | Model tier | Why this tier |
|---|---|---|
| **1. Extract** every commitment, decision and question (long transcripts: chunks in parallel) | **Nemotron Nano** | High-volume, pattern-level work — fast and cheap |
| **2. Resolve** reassignments, duplicates, timeline conflicts; set priorities & dependencies | **Nemotron Ultra** | The only step needing real multi-step reasoning |
| **3. Draft** one follow-up email per owner | **Nemotron Super** | Good writing quality at a balanced cost |

Every call is logged (step, model, tokens, latency, cost) and shown in the UI under **"Under the hood"**, together with what the same run would have cost if every step ran on Ultra. The routing table lives in [`app/llm.py`](app/llm.py); the pipeline in [`app/pipeline.py`](app/pipeline.py).

### Built to hold up in a live demo
- **Graceful degradation:** if the Ultra step fails, the app falls back to the raw Nano extraction with a warning; if email drafting fails, the plan is still returned.
- **Tolerant parsing:** strips reasoning traces and code fences, asks the model once to repair invalid JSON, and normalises odd field values.
- **Reply cache** (`LLM_CACHE=1`): identical requests are answered from disk, so development reruns cost nothing and the deployed sample runs replay instantly.
- **Abuse protection:** per-client rate limit and a daily cap keep a shared demo link from draining credits.

### Features
- Paste, upload (.txt) or pick one of three sample meetings
- Tasks with owner, due date, priority, dependencies and a one-line rationale
- Conflicts and how they were resolved · decisions · still-open questions
- One follow-up email per person, with copy buttons
- Export: copy as Markdown (checklist), download CSV or JSON

## Nebius services used

- **Nebius Token Factory** — OpenAI-compatible inference for all three Nemotron tiers.
- The web app itself is hosted on Render's free tier (see [DEPLOY.md](DEPLOY.md)); a Nebius Serverless Endpoint setup is included as an option.

## Architecture

```
Browser UI (app/static/index.html)
      │  POST /api/process
      ▼
FastAPI (app/main.py) ──► pipeline.py
                             ├─ extract  → Nemotron Nano   ┐
                             ├─ resolve  → Nemotron Ultra  ├─ Nebius Token Factory
                             └─ emails   → Nemotron Super  ┘  (api.tokenfactory.nebius.com/v1)
                             └─ RunLog: per-call model / tokens / latency → UI
```

## Setup

**Prerequisites:** Python 3.10+ and a Nebius Token Factory API key.

```bash
git clone <this repo> && cd meeting-to-actions
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then paste your key after NEBIUS_API_KEY=
python scripts/list_models.py   # checks your key + the Nemotron model IDs
python scripts/smoke_test.py    # runs the samples live and checks the hard cases
uvicorn app.main:app --reload
```

Open http://localhost:8000, pick a sample from **Load a sample…**, then **Generate action plan**.

**No key yet?** Leave `NEBIUS_API_KEY` empty — the app runs in **mock mode** (a simple offline heuristic stands in for the models) so you can try the flow end to end.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `NEBIUS_API_KEY` | — | Token Factory key. Empty → mock mode |
| `NEBIUS_BASE_URL` | `https://api.tokenfactory.nebius.com/v1/` | API endpoint |
| `NEMOTRON_NANO_MODEL` / `_SUPER_` / `_ULTRA_` | see `.env.example` | Model ID per tier |
| `MOCK_LLM` | `0` | `1` forces mock mode (saves credits during UI work) |

Optional settings (reply cache, price estimates, rate limits) are documented in [`.env.example`](.env.example).

### Tests

```bash
pytest -q
```

Tests never spend credits: they use mock mode or a fake Token Factory client, which also exercises the live-API code path (usage accounting, JSON repair, retries, cache replay). CI runs them on every push, then builds the Docker image and checks that the container starts healthy.

## Deploy

See **[DEPLOY.md](DEPLOY.md)**: one-page setup on Render's free tier (no Docker needed locally), plus optional Nebius Serverless Endpoint steps. GitHub Actions also publishes the image to `ghcr.io/swissthree/nebius-x-nividia-hackathon`.

## Sample meetings

| Sample | What it tests |
|---|---|
| [`product_sync.txt`](samples/product_sync.txt) | Task reassigned mid-meeting (help center: Dana → Marco); QA needs 3 days vs. Friday launch; answered vs. open questions |
| [`customer_escalation.txt`](samples/customer_escalation.txt) | Customer deadline vs. engineering estimate, resolved with a stopgap; SLA credit left open |
| [`eng_standup.txt`](samples/eng_standup.txt) | Dependency chain (schema → page → PDF); work reassigned for a vacation; feature-flag decision |

## Project layout

```
app/
  main.py        FastAPI routes, rate limiting
  pipeline.py    extract → resolve → emails, chunking, fallbacks
  llm.py         Token Factory client, tier routing, cost log, cache
  prompts.py     prompts per step
  schemas.py     lenient output models
  mock.py        offline stand-in used without a key
  static/        single-page UI
scripts/         list_models.py (key + model check), smoke_test.py (live checks)
samples/         demo transcripts
tests/           pytest suite
```

## How this was built

This project was **vibe coded**: built in a few days by directing an AI coding assistant (Claude, by Anthropic) rather than writing the code by hand.

- **The AI wrote** the code, tests, prompts, docs, demo video and thumbnail, from plain-language instructions.
- **I (Marcus)** chose the idea and track, set up the Nebius, GitHub and Render accounts and keys, ran the live tests on real Nemotron models, deployed the demo, and reviewed and decided on each step (for example, choosing free hosting over a paid Nebius endpoint).
- Every claim in this README was checked against real runs: the live smoke test (11/11 checks on real Nemotron output), the 45-test suite, and the deployed demo.

## License

[MIT](LICENSE)
