from pathlib import Path

import pytest

from app.config import Settings
from app.llm import LLMClient, LLMError
from app.mock import mock_responder
from app.pipeline import InputError, process_transcript

SAMPLE = (Path(__file__).resolve().parent.parent / "samples" / "product_sync.txt").read_text(encoding="utf-8")


def mock_client(responder=mock_responder) -> LLMClient:
    return LLMClient(Settings(api_key="", nano_model="nano-m", super_model="super-m", ultra_model="ultra-m"),
                     mock_responder=responder)


def test_happy_path_routes_steps_to_the_right_tiers():
    r = process_transcript(SAMPLE, client=mock_client())
    steps = [(c["step"], c["tier"], c["model"]) for c in r["routing"]["calls"]]
    assert steps == [("extract", "nano", "nano-m"), ("resolve", "ultra", "ultra-m"), ("emails", "super", "super-m")]
    assert r["mock"] is True
    assert r["warnings"] == []


def test_happy_path_produces_tasks_decisions_and_emails():
    r = process_transcript(SAMPLE, client=mock_client(), sender="Priya")
    assert set(r["participants"]) == {"Priya", "Marco", "Dana", "Sam"}
    assert len(r["tasks"]) >= 5
    assert all(t["priority"] in {"high", "medium", "low"} for t in r["tasks"])
    assert r["decisions"]
    owners = {t["owner"] for t in r["tasks"] if t["owner"]}
    assert {e["to"] for e in r["emails"]} == owners
    assert all(e["body"].rstrip().endswith("Priya") for e in r["emails"])


def test_ultra_failure_falls_back_to_extracted_tasks():
    def flaky(step, system, user):
        if step == "resolve":
            raise LLMError("ultra down")
        return mock_responder(step, system, user)

    r = process_transcript(SAMPLE, client=mock_client(flaky))
    assert r["tasks"], "fallback should still return tasks"
    assert any("Conflict resolution step failed" in w for w in r["warnings"])


def test_email_failure_is_a_warning_not_a_crash():
    def flaky(step, system, user):
        if step == "emails":
            return {"emails": [{"subject": "missing to/body"}]}  # invalid shape
        return mock_responder(step, system, user)

    r = process_transcript(SAMPLE, client=mock_client(flaky))
    assert r["emails"] == []
    assert any("Email drafting step failed" in w for w in r["warnings"])


def test_lenient_schema_accepts_odd_model_output():
    def odd(step, system, user):
        if step == "resolve":
            return {"tasks": [{"title": "Do it", "priority": "URGENT", "extra": 1}], "decisions": []}
        return mock_responder(step, system, user)

    r = process_transcript(SAMPLE, client=mock_client(odd))
    assert r["tasks"][0]["priority"] == "medium"


@pytest.mark.parametrize("text", ["", "too short", "x" * 100_001])
def test_input_validation(text):
    with pytest.raises(InputError):
        process_transcript(text, client=mock_client())
