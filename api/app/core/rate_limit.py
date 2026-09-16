"""Rate limiting for authentication endpoints (§9.4 — "blunt credential
stuffing"). A fixed-window counter per client IP, in-process.

In-process is the one real limitation worth stating plainly: this blunts
a single attacker hammering a single instance, but doesn't share state
across Cloud Run instances the way the reporting-cycle invariant's
deferred trigger does at the database layer. A shared store (Redis) is
the upgrade path if this ever needs to hold under multi-instance scale.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: float) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def __call__(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - self._window_seconds
        hits = [hit for hit in self._hits[key] if hit > window_start]
        hits.append(now)
        self._hits[key] = hits
        if len(hits) > self._max_attempts:
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts — try again in a minute",
            )


login_rate_limiter = RateLimiter(max_attempts=5, window_seconds=60)
