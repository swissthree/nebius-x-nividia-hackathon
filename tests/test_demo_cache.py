"""The recorded demo replies must replay every sample with zero live calls (judging-day safety net).

If this fails after a prompt or model change, re-record: `py scripts/smoke_test.py` then copy the
new files from .cache/llm/ into demo_cache/ (see DEPLOY.md).
"""
import json
from pathlib import Path

import pytest

from app.config import Settings
from app.llm import LLMClient
from app.pipeline import process_transcript

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = json.loads((ROOT / "samples" / "index.json").read_text(encoding="utf-8"))


class NoNetwork:
    class chat:
        class completions:
            @staticmethod
            def create(**kw):
                raise AssertionError(f"live call attempted for {kw['model']} — demo_cache is stale")


@pytest.mark.skipif(not list((ROOT / "demo_cache").glob("*.json")), reason="no recorded demo replies yet")
@pytest.mark.parametrize("sample", SAMPLES, ids=[s["id"] for s in SAMPLES])
def test_demo_cache_replays_sample(sample):
    settings = Settings(api_key="x", cache_enabled=True, cache_dir=ROOT / "demo_cache")
    client = LLMClient(settings, openai_client=NoNetwork())
    r = process_transcript((ROOT / "samples" / f"{sample['id']}.txt").read_text(encoding="utf-8"),
                           title=sample["title"], sender=sample["sender"], client=client)
    assert r["warnings"] == []
    assert all(c["cached"] for c in r["routing"]["calls"])
    assert r["tasks"] and r["emails"]
