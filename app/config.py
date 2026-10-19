"""Settings loaded from environment variables (and a local .env file if present)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _flag(name: str, default: str = "0") -> bool:
    return _env(name, default).lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default_factory=lambda: os.getenv("NEBIUS_API_KEY", "").strip())
    base_url: str = field(default_factory=lambda: _env("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"))
    nano_model: str = field(default_factory=lambda: _env("NEMOTRON_NANO_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"))
    super_model: str = field(default_factory=lambda: _env("NEMOTRON_SUPER_MODEL", "nvidia/nemotron-3-super-120b-a12b"))
    ultra_model: str = field(default_factory=lambda: _env("NEMOTRON_ULTRA_MODEL", "nvidia/Nemotron-3-Ultra-550b-a55b"))
    force_mock: bool = field(default_factory=lambda: _flag("MOCK_LLM"))

    # Nemotron 3 models reason before answering unless told not to. Reasoning only pays off where the
    # job is hard, so by default only Ultra thinks; Nano (extraction) and Super (drafting) answer directly.
    thinking_nano: bool = field(default_factory=lambda: _flag("THINKING_NANO", "0"))
    thinking_super: bool = field(default_factory=lambda: _flag("THINKING_SUPER", "0"))
    thinking_ultra: bool = field(default_factory=lambda: _flag("THINKING_ULTRA", "1"))

    # Estimated USD per 1M tokens (input, output). Verify against the Token Factory pricing page.
    nano_price: tuple[float, float] = field(default_factory=lambda: (_float("PRICE_NANO_IN", 0.06), _float("PRICE_NANO_OUT", 0.24)))
    super_price: tuple[float, float] = field(default_factory=lambda: (_float("PRICE_SUPER_IN", 0.30), _float("PRICE_SUPER_OUT", 0.90)))
    ultra_price: tuple[float, float] = field(default_factory=lambda: (_float("PRICE_ULTRA_IN", 1.00), _float("PRICE_ULTRA_OUT", 3.00)))

    # Disk cache of model replies: identical requests are answered from disk (saves credits, stable demos).
    cache_enabled: bool = field(default_factory=lambda: _flag("LLM_CACHE"))
    cache_dir: Path = field(default_factory=lambda: Path(_env("LLM_CACHE_DIR", str(ROOT / ".cache" / "llm"))))

    # Public-demo protection
    rate_limit_per_minute: int = field(default_factory=lambda: _int("RATE_LIMIT_PER_MINUTE", 5))
    daily_run_cap: int = field(default_factory=lambda: _int("DAILY_RUN_CAP", 300))

    @property
    def mock(self) -> bool:
        """Mock mode is on when forced, or automatically when no API key is configured."""
        return self.force_mock or not self.api_key


def get_settings() -> Settings:
    return Settings()
