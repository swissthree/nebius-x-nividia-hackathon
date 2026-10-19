import pytest

from app.config import Settings
from app.llm import LLMClient, LLMError, RunLog, Tier, parse_json_reply


def test_parse_plain_json():
    assert parse_json_reply('{"a": 1}') == {"a": 1}


def test_parse_strips_think_and_fences():
    reply = '<think>let me reason...</think>\nHere you go:\n```json\n{"items": [1, 2]}\n```'
    assert parse_json_reply(reply) == {"items": [1, 2]}


def test_parse_finds_object_in_prose():
    assert parse_json_reply('Sure! {"ok": true} hope that helps') == {"ok": True}


def test_parse_rejects_garbage():
    with pytest.raises(ValueError):
        parse_json_reply("no json here")


def test_mock_mode_routes_and_logs_each_tier():
    settings = Settings(api_key="", nano_model="n", super_model="s", ultra_model="u")
    client = LLMClient(settings, mock_responder=lambda step, sys_, usr: {"step": step})
    log = RunLog()
    for tier in Tier:
        out = client.chat_json(tier=tier, step=f"step-{tier.value}", system="sys", user="hello", log=log)
        assert out == {"step": f"step-{tier.value}"}
    assert [c.model for c in log.calls] == ["n", "s", "u"]
    assert all(c.mock for c in log.calls)
    assert set(log.totals_by_tier()) == {"nano", "super", "ultra"}


def test_mock_without_responder_errors():
    client = LLMClient(Settings(api_key=""))
    with pytest.raises(LLMError):
        client.chat_json(tier=Tier.NANO, step="x", system="", user="", log=RunLog())


def test_all_file_io_is_utf8():
    """Windows defaults to cp1252; every text read/write must name utf-8 or symbols like '—' and '≈' break."""
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    bad = []
    for py in [*root.glob("app/*.py"), *root.glob("scripts/*.py")]:
        for n, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\.(read_text|write_text)\(", line) and "encoding=" not in line:
                bad.append(f"{py.name}:{n}")
    assert not bad, bad
