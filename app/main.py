"""FastAPI app: JSON API + a single-page UI.

Run locally:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import get_settings
from .llm import TIER_PURPOSE, LLMError, Tier
from .pipeline import InputError, make_client, process_transcript
from .ratelimit import RateLimiter

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"
SAMPLES_DIR = ROOT / "samples"
SAMPLES = json.loads((SAMPLES_DIR / "index.json").read_text(encoding="utf-8"))
SAMPLE_IDS = {s["id"] for s in SAMPLES}

app = FastAPI(title="Meeting-to-Actions", version="0.2.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

_settings = get_settings()
_client = make_client()
_limiter = RateLimiter(_settings.rate_limit_per_minute, _settings.daily_run_cap)


class ProcessRequest(BaseModel):
    transcript: str = Field(..., description="Meeting transcript, ideally 'Name: text' per line")
    title: str = Field("Team meeting", max_length=200)
    sender: str = Field("Meeting-to-Actions", max_length=100)


def _client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "mock": _client.mock,
        "cache": _settings.cache_enabled,
        "tiers": [
            {"tier": t.value, "model": _client.model_for(t), "purpose": TIER_PURPOSE[t],
             "price_per_m": dict(zip(("input", "output"), _client.price_for(t)))}
            for t in Tier
        ],
    }


@app.get("/api/samples")
def samples() -> list[dict]:
    return SAMPLES


@app.get("/api/samples/{sample_id}", response_class=PlainTextResponse)
def sample_text(sample_id: str) -> str:
    if sample_id not in SAMPLE_IDS:  # whitelist — never build paths from user input
        raise HTTPException(status_code=404, detail="Unknown sample")
    return (SAMPLES_DIR / f"{sample_id}.txt").read_text(encoding="utf-8")


@app.get("/api/sample", response_class=PlainTextResponse, include_in_schema=False)
def sample() -> str:  # kept for backwards compatibility
    return sample_text(SAMPLES[0]["id"])


@app.post("/api/process")
def process(req: ProcessRequest, request: Request) -> dict:
    refused = _limiter.check(_client_id(request))
    if refused:
        raise HTTPException(status_code=429, detail=refused)
    try:
        return process_transcript(req.transcript, title=req.title, sender=req.sender, client=_client)
    except InputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
