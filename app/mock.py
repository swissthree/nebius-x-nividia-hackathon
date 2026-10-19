"""Offline stand-in for Nemotron so the app runs and tests pass without an API key.

It uses simple heuristics on "Name: text" transcripts — good enough to exercise the
full pipeline and UI, clearly not a replacement for the real models.
"""
from __future__ import annotations

import json
import re
from collections import OrderedDict

_LINE_RE = re.compile(r"^\s*([A-Z][\w .'-]{0,40}?)\s*:\s*(.+)$")
_TASK_RE = re.compile(r"\b(i'll|i will|i can take|can you|could you|need to|will have)\b", re.I)
_DECISION_RE = re.compile(r"\b(we decided|decided to|let's go with|agreed|owns? the)\b", re.I)
_DUE_RE = re.compile(
    r"\b(?:by\s+)?(today|tomorrow|end of (?:day|week)|monday|tuesday|wednesday|thursday|friday|saturday|sunday|next week)\b",
    re.I,
)
_URGENT = {"today", "tomorrow", "end of day"}


def _between(text: str, tag: str) -> str:
    m = re.search(rf"<{tag}>\n?(.*?)\n?</{tag}>", text, re.S)
    return m.group(1) if m else ""


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]


def _clean_title(sentence: str, names: list[str]) -> str:
    s = re.sub(r"^(okay|yes|sure|great|fine|good question)[,.!]?\s*", "", sentence, flags=re.I)
    for n in names:
        s = re.sub(rf"^{re.escape(n)},\s*", "", s)
    s = re.sub(r"^(i'll|i will|can you|could you|i can take)\s+(also\s+)?", "", s, flags=re.I)
    s = _DUE_RE.sub("", s).rstrip(" ?.!,")
    return (s[:1].upper() + s[1:]) if s else sentence


def _extract(user: str) -> dict:
    transcript = _between(user, "transcript")
    turns = [(m.group(1).strip(), m.group(2).strip()) for line in transcript.splitlines() if (m := _LINE_RE.match(line))]
    names = list(OrderedDict.fromkeys(n for n, _ in turns))
    items, n = [], 0
    for speaker, text in turns:
        for sent in _sentences(text):
            kind = None
            if _DECISION_RE.search(sent):
                kind = "decision"
            elif _TASK_RE.search(sent):
                kind = "task"
            elif sent.endswith("?") and len(sent) > 15 and not re.match(r"^(where|hmm)", sent, re.I):
                kind = "question"
            if not kind:
                continue
            owner = speaker
            addressed = next((nm for nm in names if sent.startswith(nm + ",")), None)
            if addressed and re.search(r"can you|could you", sent, re.I):
                owner = addressed
            due = _DUE_RE.search(sent)
            n += 1
            items.append({
                "id": f"i{n}", "kind": kind,
                "text": _clean_title(sent, names) if kind == "task" else sent,
                "owner": owner if kind == "task" else None,
                "due": due.group(1) if due else None,
                "evidence": sent[:120],
            })
    return {"participants": names, "items": items}


def _resolve(user: str) -> dict:
    items = json.loads(_between(user, "items") or "[]")
    tasks, decisions, questions, conflicts = [], [], [], []
    for it in items:
        if it["kind"] == "decision":
            decisions.append(it["text"])
        elif it["kind"] == "question":
            questions.append(it["text"])
        else:
            due = (it.get("due") or "").lower()
            tasks.append({
                "id": f"t{len(tasks) + 1}", "title": it["text"], "owner": it.get("owner"), "due": it.get("due"),
                "priority": "high" if due in _URGENT else "medium", "depends_on": [],
                "rationale": "Due within a day." if due in _URGENT else "Committed in the meeting.",
            })
    # merge near-duplicate tasks (same first 3 words) — keep the later owner, record the conflict
    seen: dict[str, dict] = {}
    for t in list(tasks):
        key = " ".join(t["title"].lower().split()[:3])
        if key in seen:
            prev = seen[key]
            conflicts.append({"description": f"'{t['title']}' claimed by {prev['owner']} and {t['owner']}",
                              "resolution": f"Kept the later owner, {t['owner']}."})
            tasks.remove(prev)
        seen[key] = t
    for i, t in enumerate(tasks, 1):
        t["id"] = f"t{i}"
    return {
        "summary": f"[mock] {len(tasks)} tasks, {len(decisions)} decisions and {len(questions)} open questions captured.",
        "tasks": tasks, "decisions": decisions, "open_questions": questions, "conflicts": conflicts,
    }


def _emails(system: str, user: str) -> dict:
    plan = json.loads(_between(user, "plan") or "{}")
    sender = re.search(r'Sign off as "([^"]+)"', system)
    sender = sender.group(1) if sender else "the team"
    by_owner: dict[str, list[dict]] = OrderedDict()
    for t in plan.get("tasks", []):
        if t.get("owner"):
            by_owner.setdefault(t["owner"], []).append(t)
    emails = []
    for owner, ts in by_owner.items():
        lines = "\n".join(f"- {t['title']}" + (f" (due {t['due']})" if t.get("due") else "") for t in ts)
        emails.append({
            "to": owner, "subject": "Your action items from today's meeting",
            "body": f"Hi {owner},\n\nThanks for today. Here's what you're on:\n{lines}\n\nShout if anything changes.\n\n{sender}",
        })
    return {"emails": emails}


def mock_responder(step: str, system: str, user: str) -> dict:
    step = step.split("[")[0]  # "extract[2/3]" -> "extract"
    if step == "extract":
        return _extract(user)
    if step == "resolve":
        return _resolve(user)
    if step == "emails":
        return _emails(system, user)
    raise ValueError(f"no mock for step {step!r}")
