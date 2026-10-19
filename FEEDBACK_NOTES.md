# Running feedback notes (for the submission write-up)

Add notes as you go — dated, short. Turn into the final feedback section at the end.

## Token Factory
- 2026-10-18 — Docs: OpenAI-compatible API; switching from the OpenAI SDK only needed `base_url` + key. Quick to integrate.
- 2026-10-18 — Docs note the API key is only shown once at creation — worth calling out in onboarding.
- 2026-10-18 — First live call worked: 28 models listed. Model IDs are case-sensitive and inconsistent in casing (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/Nemotron-3-Ultra-550b-a55b`, `nvidia/nemotron-3-super-120b-a12b`) — third-party listings show lowercase IDs that fail. Worth flagging. Also listed: `Nemotron-3.5-Super-VL`, `Nemotron-3_5-Lightning`.
- 2026-10-18 — Windows gotcha (ours, not Nebius): Python defaults to cp1252 file encoding; fixed by UTF-8 everywhere.
- _TODO:_ onboarding time, latency per tier, rate limits, error messages, dashboard usefulness.

## Nemotron models
- 2026-10-18 — First live smoke test: **11/11 checks passed with untuned prompts.** Ultra applied a mid-meeting reassignment (and noted it), resolved the QA-vs-Friday conflict as a staged rollout, dropped an answered question, built a schema → page → PDF dependency chain, and on its own flagged a tight 2-day window as a risk. Very strong for a first run.
- Ultra was fast for a 550B model: ~6 s per resolve step (~1.2k in / ~1.4–2.2k out tokens).
- Nano is a reasoning model by default: extraction took 12–24 s and up to ~7.2k output tokens for a ~1k-token answer. Usage beyond the 4,096 max_tokens means the first attempt was truncated mid-reasoning and our JSON-repair retry ran — i.e. default reasoning can silently double the cost of "cheap" steps. Fix: `chat_template_kwargs: {enable_thinking: false}` for Nano/Super. **Doc gap:** Token Factory docs don't say which models accept this switch.
- Small hallucination: the summary gave a deadline ("by Thursday") to a task that had none. Prompt now forbids adding owners/deadlines in the summary.
- **Reasoning switch confirmed on Token Factory** (`chat_template_kwargs.enable_thinking=false` accepted by Nano and Super). Nano extract: 12–24 s → ~2 s, ~3–7k → ~450 output tokens (−90%). Super emails: 7–9 s → ~2 s. Ultra (reasoning on) 6–22 s — now the whole latency budget. Still 11/11.
- Cost after the fix: ≈ $0.008–0.010 per meeting; Ultra's reasoning is ~80% of it. Tiered vs "same tokens on Ultra" is 24–30% cheaper. (The earlier 59–71% figure was inflated by Nano's wasted reasoning tokens — don't quote it.)
- Remaining small quality quirks: summary can still bundle a deadline onto an undated task in a list ("…and update help center articles by Thursday"); Super sometimes skips an email to the sender (product sync) and sometimes doesn't (standup).

## Other NVIDIA / Nebius tools
- _TODO:_ Serverless Endpoint deployment experience.
