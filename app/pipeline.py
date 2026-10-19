"""Meeting transcript → action plan → follow-up emails, routed across Nemotron tiers.

    1. extract  (Nemotron Nano)  — pull every commitment / decision / question, fast and cheap
                                   (long transcripts are split into chunks extracted in parallel)
    2. resolve  (Nemotron Ultra) — reason over reassignments, duplicates and timeline conflicts
    3. emails   (Nemotron Super) — draft one follow-up email per owner

If a later step fails, the pipeline degrades gracefully and reports a warning instead of crashing.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from pydantic import ValidationError

from . import prompts
from .llm import LLMClient, LLMError, RunLog, Tier
from .mock import mock_responder
from .schemas import Emails, ExtractedItem, Extraction, Resolution, Task

MIN_CHARS = 40
MAX_CHARS = 100_000
CHUNK_CHARS = 12_000   # transcripts longer than this are extracted in chunks
CHUNK_OVERLAP_LINES = 2
MAX_PARALLEL = 4


class InputError(ValueError):
    pass


def make_client() -> LLMClient:
    return LLMClient(mock_responder=mock_responder)


def split_transcript(transcript: str, chunk_chars: Optional[int] = None, overlap: Optional[int] = None) -> list[str]:
    """Split on line boundaries into ~chunk_chars pieces; repeat a few lines so no commitment is cut in half."""
    chunk_chars = chunk_chars or CHUNK_CHARS
    overlap = CHUNK_OVERLAP_LINES if overlap is None else overlap
    if len(transcript) <= chunk_chars:
        return [transcript]
    lines = transcript.splitlines()
    chunks, current, size = [], [], 0
    for line in lines:
        if current and size + len(line) + 1 > chunk_chars:
            chunks.append("\n".join(current))
            current = current[-overlap:] if overlap else []
            size = sum(len(x) + 1 for x in current)
        current.append(line)
        size += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (text or "").lower()).strip()


def merge_extractions(parts: list[Extraction]) -> Extraction:
    """Combine chunk results: keep participant order, drop items repeated by the chunk overlap, renumber ids."""
    participants: list[str] = []
    items: list[ExtractedItem] = []
    seen: set[tuple] = set()
    for part in parts:
        for p in part.participants:
            if p not in participants:
                participants.append(p)
        for it in part.items:
            key = (it.kind, _norm(it.text), _norm(it.owner or ""))
            if key in seen:
                continue
            seen.add(key)
            items.append(it.model_copy(update={"id": f"i{len(items) + 1}"}))
    return Extraction(participants=participants, items=items)


def _extract(client: LLMClient, transcript: str, log: RunLog) -> Extraction:
    chunks = split_transcript(transcript)

    def run(idx_chunk: tuple[int, str]) -> Extraction:
        idx, chunk = idx_chunk
        step = "extract" if len(chunks) == 1 else f"extract[{idx + 1}/{len(chunks)}]"
        raw = client.chat_json(
            tier=Tier.NANO, step=step, log=log,
            system=prompts.EXTRACT_SYSTEM, user=prompts.EXTRACT_USER.format(transcript=chunk),
        )
        return Extraction.model_validate(raw)

    if len(chunks) == 1:
        return run((0, chunks[0]))
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        parts = list(pool.map(run, enumerate(chunks)))
    return merge_extractions(parts)


def _fallback_resolution(extraction: Extraction) -> Resolution:
    """Used if the Ultra step fails: turn raw extracted items into a plan without conflict resolution."""
    tasks = [
        Task(id=f"t{i}", title=it.text, owner=it.owner, due=it.due)
        for i, it in enumerate((x for x in extraction.items if x.kind == "task"), 1)
    ]
    return Resolution(
        summary="Plan built directly from extracted items (conflict resolution unavailable).",
        tasks=tasks,
        decisions=[x.text for x in extraction.items if x.kind == "decision"],
        open_questions=[x.text for x in extraction.items if x.kind == "question"],
    )


def process_transcript(
    transcript: str,
    *,
    title: str = "Team meeting",
    sender: str = "Meeting-to-Actions",
    client: Optional[LLMClient] = None,
) -> dict:
    transcript = (transcript or "").strip()
    if len(transcript) < MIN_CHARS:
        raise InputError(f"Transcript is too short (minimum {MIN_CHARS} characters).")
    if len(transcript) > MAX_CHARS:
        raise InputError(f"Transcript is too long (maximum {MAX_CHARS:,} characters).")

    client = client or make_client()
    log = RunLog()
    warnings: list[str] = []

    # 1. Extract — Nano
    try:
        extraction = _extract(client, transcript, log)
    except (LLMError, ValidationError) as exc:
        raise LLMError(f"Could not extract items from the transcript: {exc}") from exc

    # 2. Resolve — Ultra
    try:
        raw = client.chat_json(
            tier=Tier.ULTRA, step="resolve", log=log,
            system=prompts.RESOLVE_SYSTEM,
            user=prompts.RESOLVE_USER.format(
                transcript=transcript,
                items_json=json.dumps([i.model_dump() for i in extraction.items], indent=1),
            ),
            max_tokens=8192,
        )
        resolution = Resolution.model_validate(raw)
    except (LLMError, ValidationError) as exc:
        warnings.append(f"Conflict resolution step failed, showing raw extracted tasks instead ({exc}).")
        resolution = _fallback_resolution(extraction)

    # 3. Follow-up emails — Super
    emails = Emails()
    if any(t.owner for t in resolution.tasks):
        try:
            raw = client.chat_json(
                tier=Tier.SUPER, step="emails", log=log,
                system=prompts.EMAILS_SYSTEM.replace("{sender}", sender),
                user=prompts.EMAILS_USER.format(title=title, plan_json=resolution.model_dump_json(indent=1)),
            )
            emails = Emails.model_validate(raw)
        except (LLMError, ValidationError) as exc:
            warnings.append(f"Email drafting step failed ({exc}).")

    return {
        "title": title,
        "mock": client.mock,
        "participants": extraction.participants,
        "extracted_items": [i.model_dump() for i in extraction.items],
        **resolution.model_dump(),
        "emails": [e.model_dump() for e in emails.emails],
        "warnings": warnings,
        "routing": log.to_dict(),
    }
