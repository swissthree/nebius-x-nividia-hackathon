# Build Progress — Meeting-to-Actions

**Hackathon:** Nebius × NVIDIA · **Deadline:** Oct 30, 2026 · **Track:** Best Apps & Agents
**Stack:** Python + FastAPI, single-page HTML UI, Nebius Token Factory (OpenAI-compatible)

> **Project location (user's rule): everything lives in `C:\Users\marcu\OneDrive\Desktop\github\projects\nebius-x-nividia-hackathon`** (Windows; GitHub remote `swissthree/nebius-x-nividia-hackathon`). A new chat should connect that folder and read this file first. Never read or print `.env` — it holds the API key.

---

## Where to pick up next session

Everything that can be built without the API key is done. The remaining work needs the key, or needs you (accounts, video).

1. ~~API key~~ ✅ · ~~model IDs~~ ✅ · ~~smoke test~~ ✅ 11/11 (Session 3)
2. ~~Reasoning switch confirmed~~ ✅ · ~~demo replies recorded~~ ✅
3. ~~First commit + push~~ ✅ (Oct 18, 23:27). ⚠️ `.env` was accidentally included because `.gitignore` line 2 had a pasted command (`.envpip install …`). Fixed `.gitignore`; removed `.env` via `git rm --cached .env` + `commit --amend` + `push --force`. Repo is **private**, so no public exposure.
   - Done: `.env` removed from the commit and force-pushed; working tree clean. User decided to keep the current key (no rotation). History check passed. **Repo made public Oct 18, 23:35** — https://github.com/swissthree/nebius-x-nividia-hackathon (license visible ✓). Keep an eye on Token Factory usage for anything unexpected.
4. Fill `FEEDBACK_NOTES.md` from what you saw (latency, quality per tier, onboarding).
5. Push to a public GitHub repo → CI runs tests **and builds the Docker image** (I couldn't build it in my sandbox — Docker Hub is blocked there).
6. Deploy per `DEPLOY.md` (record demo replies → push image → public Serverless Endpoint).
7. Finish `SUBMISSION.md` `[FILL]`s, record the video, submit by **Oct 29**.

---

## Session 3 — Oct 18, 2026 (evening): first live run ✅

- Project moved to the user's folder (see top). Key in `.env` works.
- Real model IDs (case-sensitive): Nano `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, Super `nvidia/nemotron-3-super-120b-a12b`, Ultra `nvidia/Nemotron-3-Ultra-550b-a55b`. Defaults updated. Also available: `Nemotron-3.5-Super-VL`, `Nemotron-3_5-Lightning`.
- **Smoke test: 11/11 checks passed on real Nemotron** with the prompts unchanged.
- Bug fixed: Windows wrote/read files as cp1252 → crash writing `smoke_report.md` ("≈") and garbled "—" in samples. All file I/O now UTF-8; guard test added (38 tests).
- Windows notes: use `py -m pip ...` and `py scripts/...` (pip/python not on PATH). Terminal must be in the project folder.
- Live quality: excellent (see FEEDBACK_NOTES.md). Cost 59–71% below all-Ultra. One summary hallucinated a deadline → prompt rule added.
- **Nano was slow (12–24 s, up to 7.2k tokens)** because Nemotron 3 reasons by default and the first reply got truncated → JSON-repair retry. Added per-tier reasoning switch (`THINKING_NANO/SUPER/ULTRA`, default only Ultra on) via `extra_body.chat_template_kwargs.enable_thinking=false`, auto-fallback if the endpoint rejects it; UI shows REASONING / N TRIES badges. 42 tests. **Confirmed live:** Nano ~2 s (was 12–24 s), Super ~2 s (was 7–9 s), 11/11 still. Ultra 6–22 s is now the bottleneck. ~1¢ per meeting.
- Recorded the 9 live replies into `demo_cache/`; `tests/test_demo_cache.py` proves all 3 samples replay with zero live calls (fails loudly if prompts change → re-record). 45 tests.
- Replies from the live run are cached in `.cache/llm/` → copy into `demo_cache/` before building the Docker image.

## Session 2 — Oct 18, 2026 (afternoon)

### Built
| Area | What |
|---|---|
| Cost tracking | Per-tier price estimates (env-overridable; defaults from public listings: Nano $0.06/$0.24, Super $0.30/$0.90, Ultra $1/$3 per 1M in/out). Each call logs cost + "what it would cost on Ultra". UI shows tokens, est. cost, all-Ultra cost, % saved |
| Reply cache | `LLM_CACHE=1` → identical requests answered from `.cache/llm/` (free reruns; cached calls marked in UI, `spent_usd`=0) |
| Testable live path | `LLMClient(openai_client=...)` injection; `tests/fakes.py` FakeOpenAI |
| Long transcripts | >12k chars split on line boundaries (2-line overlap), Nano extracts chunks in parallel (4 workers), merged + deduped. Limit raised to 100k chars |
| Samples | `customer_escalation.txt`, `eng_standup.txt` + `samples/index.json`; UI dropdown fills title/sender and shows "Watch for" hints; `/api/samples`, `/api/samples/{id}` (whitelisted ids) |
| Exports | Copy as Markdown checklist, CSV download, JSON download |
| UX | Old results dim while a new run is processing |
| Demo protection | `app/ratelimit.py`: per-client 5/min + 300/day global cap → HTTP 429; respects X-Forwarded-For |
| Live smoke test | `scripts/smoke_test.py`: runs samples live, 11 targeted checks, cost/latency table, `smoke_report.md` |
| Docker | `Dockerfile` (python:3.12-slim, non-root, healthcheck, proxy headers), `.dockerignore`; `demo_cache/` baked into image for instant judging-day replays |
| Deploy guide | `DEPLOY.md`: Nebius Container Registry push + public Serverless Endpoint, env secrets, teardown |
| CI | `.github/workflows/ci.yml`: pytest (mock) + docker build + container health check |
| Submission | `SUBMISSION.md`: description, 3-min video script, feedback skeleton |

### Checkpoints tested
- ✅ 37 tests passing (live path with fake client: usage/cost, JSON repair, retries, cache, full-pipeline replay; chunking; rate limiter; sample endpoints incl. path-traversal attempt; smoke-check logic)
- ✅ Smoke checks discriminate: pass on ideal output, MISS on the mock's known mistakes (3/4 miss on product sync — expected)
- ✅ Browser: all 3 samples, CSV download, savings panel, no JS errors
- ✅ Production start command + healthcheck + per-client rate limit behind proxy headers
- ⚠️ Docker image **not built** here (Docker Hub blocked in my sandbox) → CI will build it on first push

### Bugs found & fixed
- Chunk size was captured as a default argument at import time, so changing it had no effect → now read at call time.

### Known issues / notes
- Still no live run against real Nemotron — the main remaining risk. Prompts are untested on real models.
- Prices in the cost panel are estimates from third-party listings — verify on the Token Factory pricing page and update `.env`.
- Mock output is intentionally crude (doesn't apply reassignments or spot timeline conflicts).

---

## Session 1 — Oct 18, 2026 (morning)

- Decided: Meeting-to-Actions, Best Apps & Agents track, Python + FastAPI, MIT license.
- Routing: **Nano** extract → **Ultra** resolve → **Super** emails.
- Built: config, Token Factory client with tier routing + per-call log, tolerant JSON parser, prompts, lenient schemas, mock, 3-step pipeline with fallbacks, FastAPI + UI, `list_models.py`, first sample, README, LICENSE, `.env.example`, `FEEDBACK_NOTES.md`. 18 tests.
- Token Factory facts (docs.tokenfactory.nebius.com): base URL `https://api.tokenfactory.nebius.com/v1/`, env var `NEBIUS_API_KEY`, OpenAI SDK compatible; key shown only once at creation.

---

## Deploy setup (Oct 18, late)
- Nebius CLI installed in **WSL Ubuntu** (Windows has no native CLI). Open with `wsl` from PowerShell.
- Profile `hackathon` created and default (federation login). Project `project-e04a88yhbc00dhhzjh6qcs`, region **eu-west2**, tenant `emerald-urial-tenant-92m`.
- Gotcha: the interactive `nebius profile create` asked for a tenant ID; the console's `tenantuseraccount-…` ID is wrong there. Passing `--parent-id <project-…>` directly worked.
- **Chosen route (Oct 19): no local Docker.** `.github/workflows/ci.yml` runs tests, builds the image, health-checks it, and on `main` pushes `ghcr.io/swissthree/nebius-x-nividia-hackathon:latest`. GHCR package must be set **Public**. Endpoint creation steps (WSL) in DEPLOY.md; key loaded from `.env` without typing it.
- Note: I (Claude) can see terminals/browsers via computer use but can't type in them; user runs commands.

## Session 4 — Oct 19: deployment
- GitHub Actions workflow live: tests + image build + push to GHCR on `main` (needed `git push` from **PowerShell**; WSL git has no GitHub login).
- Nebius `endpoint create` → PermissionDenied every time (project/subnet/image all fine; list works). Likely billing/quota. **User doesn't want to spend money → host on Render free tier** (Docker from repo, `PORT` honored, sleeps after 15 min idle). `DAILY_RUN_CAP` lowered to 50. DEPLOY.md/README/SUBMISSION/FEEDBACK updated.
- ✅ **Live: https://meeting-to-actions.onrender.com** (Render service `meeting-to-actions`, Free $0 plan, Docker, health `/api/health`, env: NEBIUS_API_KEY secret, LLM_CACHE=1, RATE_LIMIT_PER_MINUTE=5, DAILY_RUN_CAP=50). Auto-deploys on push to `main`.
- Verified in browser: LIVE mode, correct model IDs, sample replays from cache (0.2 s), new transcript live 7.6 s / ≈$0.005 with correct reassignment + dependency.
- ✅ Demo video recorded by Claude (1:40, captions, no voiceover): `meeting-to-actions-demo.mp4` in the project folder (git-ignored). Recorded locally replaying the recorded real Nemotron runs (`demo_cache/`); Token Factory dashboard not shown.
- ✅ Video on YouTube: https://www.youtube.com/watch?v=mNIgZXrIAU0 (linked in README). Vibe-coding disclosure added to README + SUBMISSION.
- **Remaining:** user fills in the hackathon form from SUBMISSION.md and submits (deadline Oct 30). Old note: optional voiceover; (was: record ≤3 min video) (script in SUBMISSION.md), upload public to YouTube, add link to README; fill remaining [FILL]s in SUBMISSION.md (feedback onboarding notes); submit by Oct 29.

## Next up (after the live run)

- [ ] Prompt tuning from smoke results (budget: 1 session)
- [ ] Public GitHub repo + green CI
- [ ] Deploy (DEPLOY.md) — aim for Oct 22 so there's slack
- [ ] Polish ideas if time allows: show $ per tier in the routing rows; a "why" tooltip on conflicts; audio upload (transcription) — stretch only
- [ ] Video + submission text, submit by Oct 29
