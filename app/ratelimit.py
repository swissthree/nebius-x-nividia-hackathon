"""Tiny in-memory limiter for the public demo: per-client requests per minute + a global daily cap.

It protects hackathon credits from a judge's link being shared around. Single-process only,
which is all a demo deployment needs.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from datetime import date
from typing import Callable, Optional


class RateLimiter:
    def __init__(self, per_minute: int, daily_cap: int, clock: Callable[[], float] = time.time,
                 today: Callable[[], date] = date.today):
        self.per_minute, self.daily_cap = per_minute, daily_cap
        self._clock, self._today = clock, today
        self._hits: dict[str, deque] = defaultdict(deque)
        self._day, self._day_count = today(), 0
        self._lock = threading.Lock()

    def check(self, client_id: str) -> Optional[str]:
        """Record a request. Returns None if allowed, or a human-readable reason if refused."""
        now = self._clock()
        with self._lock:
            if self._today() != self._day:
                self._day, self._day_count = self._today(), 0
            if self.daily_cap > 0 and self._day_count >= self.daily_cap:
                return "The demo has hit its daily limit — please try again tomorrow."
            hits = self._hits[client_id]
            while hits and now - hits[0] > 60:
                hits.popleft()
            if self.per_minute > 0 and len(hits) >= self.per_minute:
                wait = int(60 - (now - hits[0])) + 1
                return f"Too many requests — please wait {wait}s and try again."
            hits.append(now)
            self._day_count += 1
            return None
