import os

os.environ["MOCK_LLM"] = "1"  # API tests never spend credits
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_index_serves_ui():
    r = client.get("/")
    assert r.status_code == 200
    assert "Meeting-to-Actions" in r.text


def test_health_lists_three_tiers():
    h = client.get("/api/health").json()
    assert h["mock"] is True
    assert [t["tier"] for t in h["tiers"]] == ["nano", "super", "ultra"]


def test_process_sample_end_to_end():
    sample = client.get("/api/sample").text
    r = client.post("/api/process", json={"transcript": sample, "title": "Sync", "sender": "Priya"})
    assert r.status_code == 200
    body = r.json()
    assert body["tasks"] and body["emails"]
    assert [c["tier"] for c in body["routing"]["calls"]] == ["nano", "ultra", "super"]


def test_process_rejects_short_transcript():
    r = client.post("/api/process", json={"transcript": "hi"})
    assert r.status_code == 422
    assert "too short" in r.json()["detail"]


def test_samples_listed_and_loadable():
    samples = client.get("/api/samples").json()
    assert len(samples) >= 3
    for s in samples:
        r = client.get(f"/api/samples/{s['id']}")
        assert r.status_code == 200 and len(r.text) > 200


def test_unknown_sample_is_404_not_a_file_read():
    assert client.get("/api/samples/..%2F..%2Fapp%2Fconfig").status_code == 404
    assert client.get("/api/samples/nope").status_code == 404


def test_rate_limit_returns_429(monkeypatch):
    from app import main
    from app.ratelimit import RateLimiter
    monkeypatch.setattr(main, "_limiter", RateLimiter(per_minute=1, daily_cap=100))
    sample = client.get("/api/samples/product_sync").text
    assert client.post("/api/process", json={"transcript": sample}).status_code == 200
    r = client.post("/api/process", json={"transcript": sample})
    assert r.status_code == 429 and "wait" in r.json()["detail"]


def test_health_reports_prices():
    tiers = client.get("/api/health").json()["tiers"]
    assert all(t["price_per_m"]["input"] > 0 for t in tiers)
