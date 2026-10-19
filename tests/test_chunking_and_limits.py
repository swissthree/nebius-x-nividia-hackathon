from datetime import date

from app.config import Settings
from app.llm import LLMClient
from app.mock import mock_responder
from app.pipeline import merge_extractions, process_transcript, split_transcript
from app.ratelimit import RateLimiter
from app.schemas import Extraction


def test_short_transcript_is_one_chunk():
    assert split_transcript("A: hi\nB: hello", chunk_chars=1000) == ["A: hi\nB: hello"]


def test_long_transcript_splits_on_lines_with_overlap():
    lines = [f"P{i % 3}: line number {i} with some words" for i in range(200)]
    chunks = split_transcript("\n".join(lines), chunk_chars=1000, overlap=2)
    assert len(chunks) > 1
    assert all(len(c) <= 1100 for c in chunks)
    for a, b in zip(chunks, chunks[1:]):  # last 2 lines of one chunk start the next
        assert a.splitlines()[-2:] == b.splitlines()[:2]
    joined = set(l for c in chunks for l in c.splitlines())
    assert joined == set(lines), "no line may be lost"


def test_merge_dedupes_overlap_and_renumbers():
    a = Extraction.model_validate({"participants": ["A", "B"], "items": [
        {"id": "i1", "kind": "task", "text": "Ship it", "owner": "A"},
        {"id": "i2", "kind": "task", "text": "Write docs", "owner": "B"}]})
    b = Extraction.model_validate({"participants": ["B", "C"], "items": [
        {"id": "i1", "kind": "task", "text": "Write docs.", "owner": "B"},   # repeated by overlap
        {"id": "i2", "kind": "question", "text": "Who owns QA?"}]})
    m = merge_extractions([a, b])
    assert m.participants == ["A", "B", "C"]
    assert [i.text for i in m.items] == ["Ship it", "Write docs", "Who owns QA?"]
    assert [i.id for i in m.items] == ["i1", "i2", "i3"]


def test_long_transcript_runs_parallel_nano_chunks(monkeypatch):
    monkeypatch.setattr("app.pipeline.CHUNK_CHARS", 600)
    turns = [f"{n}: I'll handle item {i} by Friday." for i, n in enumerate(["Ana", "Ben", "Cy"] * 20)]
    client = LLMClient(Settings(api_key=""), mock_responder=mock_responder)
    r = process_transcript("\n".join(turns), client=client)
    extract_steps = [c["step"] for c in r["routing"]["calls"] if c["step"].startswith("extract")]
    assert len(extract_steps) > 1 and all(s.startswith("extract[") for s in extract_steps)
    assert all(c["tier"] == "nano" for c in r["routing"]["calls"] if c["step"].startswith("extract"))
    assert len(r["extracted_items"]) == 60, "every commitment captured exactly once"


def test_rate_limiter_per_minute_and_window():
    t = [1000.0]
    rl = RateLimiter(per_minute=2, daily_cap=100, clock=lambda: t[0])
    assert rl.check("ip") is None and rl.check("ip") is None
    assert "wait" in rl.check("ip")
    assert rl.check("other-ip") is None, "limits are per client"
    t[0] += 61
    assert rl.check("ip") is None


def test_rate_limiter_daily_cap_resets_next_day():
    day = [date(2026, 10, 18)]
    rl = RateLimiter(per_minute=0, daily_cap=2, today=lambda: day[0])
    assert rl.check("a") is None and rl.check("b") is None
    assert "daily limit" in rl.check("c")
    day[0] = date(2026, 10, 19)
    assert rl.check("c") is None
