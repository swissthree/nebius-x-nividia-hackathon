"""Make sure the live smoke-test checks actually discriminate good output from bad."""
import importlib.util
from pathlib import Path

from app.config import Settings
from app.llm import LLMClient
from app.mock import mock_responder
from app.pipeline import process_transcript

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("smoke", ROOT / "scripts" / "smoke_test.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)

IDEAL_PRODUCT_SYNC = {
    "tasks": [
        {"title": "Merge rate-limiting fix", "owner": "Marco", "due": "Wednesday", "depends_on": []},
        {"title": "Update help center articles for settings page", "owner": "Marco", "due": None, "depends_on": []},
        {"title": "Draft rollback runbook", "owner": "Marco", "due": "Thursday", "depends_on": []},
    ],
    "conflicts": [{"description": "QA needs 3 days but launch is Friday", "resolution": "Staged 10% rollout Friday"}],
    "decisions": ["Ship to 10% of users Friday, 100% after QA sign-off"],
    "open_questions": ["Does legal need to review data-retention text?"],
}


def test_checks_pass_on_ideal_output():
    for desc, check in smoke.CHECKS["product_sync"]:
        assert check(IDEAL_PRODUCT_SYNC), desc


def test_checks_catch_the_mocks_known_mistakes():
    client = LLMClient(Settings(api_key=""), mock_responder=mock_responder)
    r = process_transcript((ROOT / "samples" / "product_sync.txt").read_text(encoding="utf-8"), client=client)
    results = {desc: bool(check(r)) for desc, check in smoke.CHECKS["product_sync"]}
    assert not results["Help-center articles end up owned by Marco only (reassignment applied)"]
    assert not results["QA-time vs Friday-launch conflict is flagged"]


def test_every_sample_has_checks():
    import json
    ids = {s["id"] for s in json.loads((ROOT / "samples" / "index.json").read_text(encoding="utf-8"))}
    assert ids == set(smoke.CHECKS)
