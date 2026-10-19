# Submission drafts

Everything here is a draft to finish once the live run is done. Items marked `[FILL]` need real numbers or links.

---

## 1. Project description (for the submission form)

**Meeting-to-Actions** turns a raw meeting transcript into a conflict-free action plan: every task with an owner, deadline, priority and dependencies, plus a ready-to-send follow-up email for each person.

**The problem.** Meetings end with messy, half-made commitments. Tasks get reassigned mid-call, deadlines clash with each other, and questions get answered three minutes after they're asked. A plain summariser copies that mess into its notes. Team leads then spend 15–30 minutes after each meeting untangling who actually owns what, and the follow-up email often never goes out.

**Who it's for.** Team leads, project managers, and anyone who runs recurring meetings: product syncs, customer escalations, standups.

**How it works.** A three-step pipeline routes each job to the smallest NVIDIA Nemotron model that does it well, all served by Nebius Token Factory:

1. **Nemotron Nano** extracts every commitment, decision and question. Long transcripts are split into chunks and extracted in parallel.
2. **Nemotron Ultra** reasons over the whole meeting. It applies reassignments, merges duplicates, flags timeline conflicts, drops questions that were answered, and sets priorities and dependencies.
3. **Nemotron Super** drafts one personalised follow-up email per owner.

The UI shows an "Under the hood" panel with which model handled each step, tokens, latency and cost. Only Ultra is allowed to reason before answering. Turning reasoning off for Nano and Super cut extraction from ~20 s to ~2 s and its tokens by ~90%, with no loss in accuracy. A whole meeting costs about one cent. If the Ultra step fails, the app falls back to the raw Nano extraction instead of erroring.

**Built with:** Nebius Token Factory (OpenAI-compatible API) · NVIDIA Nemotron 3 Nano / Super / Ultra · Nebius Serverless Endpoint (hosting) · Python, FastAPI.

---

## 2. Demo video script (≤ 3:00)

Record from the deployed URL with the sample replies cached, so nothing can stall.

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
- Integration: switching the OpenAI SDK over took two settings (`base_url` + key). Moving between Nemotron tiers is just a model-ID change, which made tiered routing trivial to build.
- `[FILL]` Onboarding: time from signup to first successful call; anything confusing.
- `[FILL]` Latency per tier on our workload (from smoke_report.md).
- `[FILL]` Rate limits / errors hit, and how clear the error messages were.
- `[FILL]` Dashboard: usefulness of per-model usage for tracking credit spend.
- Docs gap: the API key is shown only once at creation. Easy to miss.

**NVIDIA Nemotron**
- `[FILL]` Nano: extraction recall on our samples; JSON reliability.
- `[FILL]` Ultra: did it apply the reassignment and flag the QA/Friday conflict? (smoke test checks)
- `[FILL]` Super: email tone and length adherence.
- `[FILL]` Did reasoning traces (`<think>`) show up in content? (Our parser strips them either way.)

**Nebius Serverless Endpoint**
- `[FILL]` Deploy experience: registry push, endpoint creation, time to live URL, logs.

---

## 4. Built during the submission period

Everything. The repository was created on Oct 18, 2026 during the hackathon; see git history.
