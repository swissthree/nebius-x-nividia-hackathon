# Submission drafts

Ready-to-paste text for the submission form. Only the YouTube link is still missing.

---

## 0. Before switching the repo to public
- [x] `git log --all --stat` shows no `.env`
- [x] Repo public: https://github.com/swissthree/nebius-x-nividia-hackathon
- [x] Demo live: https://meeting-to-actions.onrender.com
- [ ] Upload `meeting-to-actions-demo.mp4` to YouTube as **Public**, test logged out
- [ ] Video link in README

## 1. Project description (for the submission form)

**Meeting-to-Actions** turns a raw meeting transcript into a conflict-free action plan: every task with an owner, deadline, priority and dependencies, plus a ready-to-send follow-up email for each person.

**The problem.** Meetings end with messy, half-made commitments. Tasks get reassigned mid-call, deadlines clash with each other, and questions get answered three minutes after they're asked. A plain summariser copies that mess into its notes. Team leads then spend 15–30 minutes after each meeting untangling who actually owns what, and the follow-up email often never goes out.

**Who it's for.** Team leads, project managers, and anyone who runs recurring meetings: product syncs, customer escalations, standups.

**How it works.** A three-step pipeline routes each job to the smallest NVIDIA Nemotron model that does it well, all served by Nebius Token Factory:

1. **Nemotron Nano** extracts every commitment, decision and question. Long transcripts are split into chunks and extracted in parallel.
2. **Nemotron Ultra** reasons over the whole meeting. It applies reassignments, merges duplicates, flags timeline conflicts, drops questions that were answered, and sets priorities and dependencies.
3. **Nemotron Super** drafts one personalised follow-up email per owner.

The UI shows an "Under the hood" panel with which model handled each step, tokens, latency and cost. Only Ultra is allowed to reason before answering. Turning reasoning off for Nano and Super cut extraction from ~20 s to ~2 s and its tokens by ~90%, with no loss in accuracy. A whole meeting costs about one cent. If the Ultra step fails, the app falls back to the raw Nano extraction instead of erroring.

**Built with:** Nebius Token Factory (OpenAI-compatible API) · NVIDIA Nemotron 3 Nano / Super / Ultra · Python, FastAPI.

---

## 2. Demo video script (≤ 3:00)

Record from https://meeting-to-actions.onrender.com (open it a minute early to wake it up). Samples replay instantly from the recorded replies.

| Time | On screen | Say (roughly) |
|---|---|---|
| 0:00–0:20 | Title card → app home | "Every meeting ends with a mess of commitments. Tasks change hands, deadlines clash, and nobody sends the follow-up. Meeting-to-Actions fixes that in about fifteen seconds." |
| 0:20–0:40 | Pick **Product launch sync**; scroll the transcript | "Here's a real-style launch meeting. Watch two things. The help-center work moves from Dana to Marco mid-meeting, and QA needs three days but marketing already announced Friday." |
| 0:40–1:30 | Click **Generate** → results | Point at: Marco owns help-center (Dana's copy is gone) · conflict card for QA vs Friday with the staged-rollout resolution · the rollback-runbook question is *not* listed as open, because it was answered · priorities and dependencies. |
| 1:30–1:50 | Follow-up emails → Copy · tasks → **Copy as Markdown** | "Each person gets their own email with only their tasks. One click to copy, or export the whole plan to Markdown or CSV." |
| 1:50–2:30 | **Under the hood** panel; then the Token Factory dashboard | "Three NVIDIA Nemotron models, each sized to its job. Nano does cheap extraction, Ultra is reserved for the hard reasoning, Super writes. Reasoning is switched on only for Ultra. That took extraction from twenty seconds to two, and a whole meeting costs about a cent. Everything runs on Nebius Token Factory." Show the dashboard usage graph. |
| 2:30–2:50 | Paste a different transcript (e.g. the standup) → quick result | "It's general. Here's a standup with a dependency chain and a vacation handover." |
| 2:50–3:00 | README / repo URL | "Open source under MIT. Link's below. Thanks!" |

Checklist: upload as **Public** on YouTube → open the link in a logged-out window.

---

## 3. Feedback on Nebius & NVIDIA tools (draft from FEEDBACK_NOTES.md)

**Nebius Token Factory**
- **Integration was the easiest part of the build.** The OpenAI SDK worked after changing two settings (`base_url` and the key). Moving between Nemotron tiers is just a model-ID change, which made tiered routing trivial.
- **Onboarding:** from creating the API key to the first successful call took about 25 minutes, most of it Windows setup on our side rather than Token Factory.
- **Model IDs are case-sensitive and inconsistently cased** (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/Nemotron-3-Ultra-550b-a55b`, `nvidia/nemotron-3-super-120b-a12b`). Lowercase IDs from third-party listings fail with a not-found error. A consistent naming scheme, or case-insensitive matching, would save new users time.
- **Reasoning control is undocumented.** Nemotron 3 models reason by default. `chat_template_kwargs: {"enable_thinking": false}` worked on Token Factory for Nano and Super, but we found it in NVIDIA's model docs, not in Token Factory's. A per-model note on which switches are supported would help.
- **Reliability:** no rate limits or API errors hit during development or the live demo.
- **Latency on our workload** (≈1.2k input tokens per step): Nano ~2 s, Super ~1–2 s, Ultra 4–22 s with reasoning on. A full meeting is about 8–25 s end to end and costs ≈ $0.005–0.01.
- Small docs gap: the API key is shown only once at creation, which is easy to miss.

**NVIDIA Nemotron**
- **Ultra's reasoning was the standout.** On untuned prompts it passed all 11 of our targeted checks. It applied mid-meeting reassignments (and noted them), resolved a QA-time vs launch-date conflict as the team's staged rollout, dropped questions that were answered later in the meeting, built dependency chains (schema → page → PDF), and flagged a tight two-day window as a risk on its own.
- **Nano is a reasoning model by default, and that matters for "cheap" steps.** With reasoning on, extraction took 12–24 s and up to ~7k output tokens for a ~500-token answer. The first reply ran past `max_tokens` and needed a retry, so the cheap step quietly cost double. With reasoning off: ~2 s, ~90% fewer tokens, same accuracy.
- **Super** wrote short, correctly scoped follow-up emails (each person gets only their own tasks). One minor inconsistency: it sometimes skips an email to the meeting's own sender.
- **JSON output was reliable** on all three tiers once reasoning was off for Nano. With reasoning on, Nano's truncated replies were the only JSON failures we saw.
- One small hallucination: a summary once attached a deadline to a task that had none. A prompt rule fixed most of it.

**Nebius AI Cloud (Serverless Endpoints)**
- Tried to host the demo on a Serverless Endpoint. CLI setup worked (WSL on Windows; no native Windows CLI). `nebius ai endpoint list` worked, but `create` returned a bare `PermissionDenied` even with explicit project, subnet and a published public image. The error didn't say what was missing (billing? quota? role?), which made it hard to fix. Hosted the web app on a free host instead; all inference still runs on Token Factory.

---

## 4. Built during the submission period

Everything. The repository was created on Oct 18, 2026, during the hackathon; see the git history.

**How it was built:** this project was vibe coded. The code, tests, prompts, docs, demo video and thumbnail were written by an AI coding assistant (Claude, by Anthropic), directed through plain-language instructions. I chose the idea and track, set up the Nebius, GitHub and Render accounts and keys, ran the live tests on real Nemotron models, deployed the demo, and reviewed each step.
