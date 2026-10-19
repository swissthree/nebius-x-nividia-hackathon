"""Tests for the non-mock code path (what runs once NEBIUS_API_KEY is set), using a fake client."""
import pytest

from app.config import Settings
from app.llm import LLMClient, LLMError, RunLog, Tier
from tests.fakes import FakeOpenAI


def settings(tmp_path, cache=False):
    return Settings(
        api_key="test-key", nano_model="n", super_model="s", ultra_model="u",
        nano_price=(0.06, 0.24), super_price=(0.30, 0.90), ultra_price=(1.0, 3.0),
        cache_enabled=cache, cache_dir=tmp_path / "cache",
    )


def test_live_call_records_usage_and_cost(tmp_path):
    fake = FakeOpenAI(['{"ok": true}'], prompt_tokens=1_000_000, completion_tokens=0)
    client = LLMClient(settings(tmp_path), openai_client=fake)
    log = RunLog()
    assert client.chat_json(tier=Tier.NANO, step="extract", system="s", user="u", log=log) == {"ok": True}
    call = log.calls[0]
    assert (call.model, call.mock, call.cached) == ("n", False, False)
    assert call.cost_usd == pytest.approx(0.06) and call.spent_usd == pytest.approx(0.06)
    assert call.ultra_cost_usd == pytest.approx(1.0)
    assert fake.requests[0]["model"] == "n"


def test_bad_json_gets_one_repair_attempt(tmp_path):
    fake = FakeOpenAI(["sorry, here it is: not json", '{"fixed": 1}'])
    log = RunLog()
    out = LLMClient(settings(tmp_path), openai_client=fake).chat_json(tier=Tier.SUPER, step="emails", system="s", user="u", log=log)
    assert out == {"fixed": 1}
    assert len(fake.requests) == 2
    assert "not valid JSON" in fake.requests[1]["messages"][-1]["content"]
    assert log.calls[0].prompt_tokens == 200  # usage summed across both attempts


def test_api_errors_raise_after_retry(tmp_path, monkeypatch):
    monkeypatch.setattr("app.llm.time.sleep", lambda s: None)
    fake = FakeOpenAI([RuntimeError("503"), RuntimeError("503")])
    log = RunLog()
    with pytest.raises(LLMError, match="503"):
        LLMClient(settings(tmp_path), openai_client=fake).chat_json(tier=Tier.ULTRA, step="resolve", system="s", user="u", log=log)
    assert log.calls[0].ok is False


def test_cache_serves_repeat_requests_for_free(tmp_path):
    fake = FakeOpenAI(['{"v": 1}'])
    client = LLMClient(settings(tmp_path, cache=True), openai_client=fake)
    log = RunLog()
    first = client.chat_json(tier=Tier.ULTRA, step="resolve", system="s", user="same", log=log)
    second = client.chat_json(tier=Tier.ULTRA, step="resolve", system="s", user="same", log=log)
    assert first == second == {"v": 1}
    assert len(fake.requests) == 1, "second call must come from cache"
    assert log.calls[1].cached and log.calls[1].spent_usd == 0
    assert log.calls[1].prompt_tokens == log.calls[0].prompt_tokens


def test_savings_vs_all_ultra(tmp_path):
    fake = FakeOpenAI(['{"a":1}', '{"b":1}'], prompt_tokens=1_000_000, completion_tokens=0)
    client = LLMClient(settings(tmp_path), openai_client=fake)
    log = RunLog()
    client.chat_json(tier=Tier.NANO, step="x", system="s", user="1", log=log)
    client.chat_json(tier=Tier.ULTRA, step="y", system="s", user="2", log=log)
    d = log.to_dict()
    assert d["total_cost_usd"] == pytest.approx(1.06)
    assert d["all_ultra_cost_usd"] == pytest.approx(2.0)
    assert d["savings_pct"] == pytest.approx(47.0)


def test_full_pipeline_replays_from_cache_for_demo(tmp_path):
    """A recorded sample run must replay completely from cache — this is what the deployed demo relies on."""
    import json
    from pathlib import Path
    from app.mock import mock_responder
    from app.pipeline import process_transcript

    class Live(FakeOpenAI):
        def _create(self, **kw):
            sysmsg = kw["messages"][0]["content"]
            step = "extract" if "extract action items" in sysmsg else "resolve" if "conflict-free" in sysmsg else "emails"
            self.replies = [json.dumps(mock_responder(step, sysmsg, kw["messages"][1]["content"]))]
            return super()._create(**kw)

    transcript = (Path(__file__).resolve().parent.parent / "samples" / "product_sync.txt").read_text(encoding="utf-8")
    first_fake = Live([])
    first = process_transcript(transcript, title="T", sender="S", client=LLMClient(settings(tmp_path, cache=True), openai_client=first_fake))
    assert len(first_fake.requests) == 3

    replay_fake = Live([])
    second = process_transcript(transcript, title="T", sender="S", client=LLMClient(settings(tmp_path, cache=True), openai_client=replay_fake))
    assert replay_fake.requests == [], "replay must not call the API"
    assert all(c["cached"] for c in second["routing"]["calls"])
    assert second["tasks"] == first["tasks"] and second["emails"] == first["emails"]
    assert second["routing"]["spent_usd"] == 0 and second["routing"]["savings_pct"] == first["routing"]["savings_pct"]


def test_reasoning_switch_per_tier(tmp_path):
    """Only Ultra reasons by default; Nano and Super get the Nemotron enable_thinking=False switch."""
    fake = FakeOpenAI(['{"a":1}', '{"b":1}', '{"c":1}'])
    client = LLMClient(settings(tmp_path), openai_client=fake)
    log = RunLog()
    for tier in (Tier.NANO, Tier.SUPER, Tier.ULTRA):
        client.chat_json(tier=tier, step=tier.value, system="s", user=tier.value, log=log)
    sent = [r.get("extra_body") for r in fake.requests]
    off = {"chat_template_kwargs": {"enable_thinking": False}}
    assert sent == [off, off, None]
    assert [c.thinking for c in log.calls] == [False, False, True]


def test_reasoning_switch_falls_back_if_endpoint_rejects_it(tmp_path):
    class BadRequest(Exception):
        status_code = 400

    fake = FakeOpenAI([BadRequest("unknown field chat_template_kwargs"), '{"ok":1}', '{"ok":2}'])
    client = LLMClient(settings(tmp_path), openai_client=fake)
    log = RunLog()
    assert client.chat_json(tier=Tier.NANO, step="x", system="s", user="1", log=log) == {"ok": 1}
    assert "extra_body" in fake.requests[0] and "extra_body" not in fake.requests[1]
    client.chat_json(tier=Tier.NANO, step="y", system="s", user="2", log=log)
    assert "extra_body" not in fake.requests[2], "remembers the endpoint doesn't support it"


def test_other_api_errors_are_not_mistaken_for_a_rejected_switch(tmp_path, monkeypatch):
    monkeypatch.setattr("app.llm.time.sleep", lambda s: None)
    fake = FakeOpenAI([RuntimeError("timeout after 4000 ms"), '{"ok":1}'])
    client = LLMClient(settings(tmp_path), openai_client=fake)
    client.chat_json(tier=Tier.NANO, step="x", system="s", user="1", log=RunLog())
    assert all("extra_body" in r for r in fake.requests), "switch must stay on after an unrelated error"


def test_attempts_are_recorded(tmp_path):
    fake = FakeOpenAI(["truncated {", '{"ok":1}'])
    log = RunLog()
    LLMClient(settings(tmp_path), openai_client=fake).chat_json(tier=Tier.NANO, step="x", system="s", user="u", log=log)
    assert log.calls[0].attempts == 2
