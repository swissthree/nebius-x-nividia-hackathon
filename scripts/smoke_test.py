"""Live smoke test: run the sample transcripts through real Nemotron models and check the hard parts.

Usage:
    python scripts/smoke_test.py                 # all samples
    python scripts/smoke_test.py product_sync    # one sample
    python scripts/smoke_test.py --no-cache      # force fresh model calls

Needs NEBIUS_API_KEY in .env. Results are cached under .cache/llm/ (so re-runs and demos cost nothing)
and a report is written to smoke_report.md — paste observations into FEEDBACK_NOTES.md.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if "--no-cache" not in sys.argv:
    os.environ.setdefault("LLM_CACHE", "1")

from app.config import get_settings  # noqa: E402
from app.llm import LLMError  # noqa: E402
from app.pipeline import make_client, process_transcript  # noqa: E402


def _has(text, *words):
    t = (text or "").lower()
    return any(w in t for w in words)


def _tasks(r, *words):
    return [t for t in r["tasks"] if _has(t["title"], *words)]


# Each check: (description, function(result) -> bool). These are the things the mock can't do.
CHECKS = {
    "product_sync": [
        ("Help-center articles end up owned by Marco only (reassignment applied)",
         lambda r: _tasks(r, "help center") and all(t["owner"] == "Marco" for t in _tasks(r, "help center"))),
        ("QA-time vs Friday-launch conflict is flagged",
         lambda r: any(_has(c["description"] + " " + (c.get("resolution") or ""), "qa", "friday", "monday") for c in r["conflicts"])),
        ("Answered question about the rollback runbook is NOT left open",
         lambda r: not any(_has(q, "rollback") for q in r["open_questions"])),
        ("Staged-rollout decision captured",
         lambda r: any(_has(d, "10%", "staged", "rollout") for d in r["decisions"])),
    ],
    "customer_escalation": [
        ("Tom owns the stopgap timeout increase",
         lambda r: any(t["owner"] == "Tom" for t in _tasks(r, "timeout"))),
        ("Customer deadline vs fix estimate recorded as a resolved conflict",
         lambda r: any(_has(c.get("resolution") or "", "stopgap", "timeout", "temporary") for c in r["conflicts"])),
        ("SLA credit tracked (open question or Elena task)",
         lambda r: any(_has(q, "sla", "credit") for q in r["open_questions"]) or bool(_tasks(r, "sla", "credit", "billing"))),
        ("Mei's test (customer side) captured",
         lambda r: any(_has(t["owner"] or "", "mei", "ravi") for t in r["tasks"])),
    ],
    "eng_standup": [
        ("Invoice PDF generator reassigned to Ken",
         lambda r: _tasks(r, "pdf") and any(t["owner"] == "Ken" for t in _tasks(r, "pdf", "invoice"))),
        ("Billing page depends on the schema task",
         lambda r: any(t["depends_on"] for t in _tasks(r, "billing page"))),
        ("Feature-flag decision captured",
         lambda r: any(_has(d, "feature flag", "flag") for d in r["decisions"])),
    ],
}


def main() -> int:
    s = get_settings()
    if s.mock:
        print("NEBIUS_API_KEY is not set (or MOCK_LLM=1). Add your key to .env first.")
        return 1

    samples = json.loads((ROOT / "samples" / "index.json").read_text(encoding="utf-8"))
    wanted = [a for a in sys.argv[1:] if not a.startswith("--")]
    if wanted:
        samples = [x for x in samples if x["id"] in wanted]

    client = make_client()
    report = [f"# Smoke test — {time.strftime('%Y-%m-%d %H:%M')}", "",
              f"Models: nano=`{s.nano_model}` super=`{s.super_model}` ultra=`{s.ultra_model}`", ""]
    passed = total = 0
    for sample in samples:
        print(f"\n=== {sample['label']} ===")
        transcript = (ROOT / "samples" / f"{sample['id']}.txt").read_text(encoding="utf-8")
        try:
            r = process_transcript(transcript, title=sample["title"], sender=sample["sender"], client=client)
        except LLMError as exc:
            print("  FAILED:", exc)
            report += [f"## {sample['label']}", "", f"**Pipeline failed:** {exc}", ""]
            total += len(CHECKS.get(sample["id"], []))
            continue

        report += [f"## {sample['label']}", "", "| Step | Tier | Tokens | Latency | Cached |", "|---|---|---|---|---|"]
        for c in r["routing"]["calls"]:
            flags = " ".join(x for x in ("reasoning" if c.get("thinking") else "", "(cached)" if c["cached"] else "",
                                         f"{c.get('attempts', 1)} tries" if c.get("attempts", 1) > 1 else "") if x)
            line = f"  {c['step']:<14} {c['tier']:<6} {c['prompt_tokens']:>6}+{c['completion_tokens']:<6} {c['latency_ms'] / 1000:>6.1f}s  {flags}"
            print(line)
            report.append(f"| {c['step']} | {c['tier']} | {c['prompt_tokens']}+{c['completion_tokens']} | {c['latency_ms'] / 1000:.1f}s | {'yes' if c['cached'] else ''} |")
        rt = r["routing"]
        print(f"  cost ≈ ${rt['total_cost_usd']:.4f} (all-Ultra ≈ ${rt['all_ultra_cost_usd']:.4f}, {rt['savings_pct']}% saved)")
        for w in r["warnings"]:
            print("  WARNING:", w)

        report += ["", f"Cost ≈ ${rt['total_cost_usd']:.4f} vs all-Ultra ≈ ${rt['all_ultra_cost_usd']:.4f} ({rt['savings_pct']}% saved)", ""]
        for desc, check in CHECKS.get(sample["id"], []):
            total += 1
            try:
                ok = bool(check(r))
            except Exception:
                ok = False
            passed += ok
            print(f"  [{'PASS' if ok else 'MISS'}] {desc}")
            report.append(f"- {'✅' if ok else '❌'} {desc}")
        report += ["", "<details><summary>Full output</summary>", "", "```json",
                   json.dumps({k: r[k] for k in ("summary", "tasks", "conflicts", "decisions", "open_questions")}, indent=1),
                   "```", "</details>", ""]

    print(f"\n{passed}/{total} checks passed. Report: smoke_report.md")
    (ROOT / "smoke_report.md").write_text("\n".join(report), encoding="utf-8")
    return 0 if passed == total else 2


if __name__ == "__main__":
    sys.exit(main())
