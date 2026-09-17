from __future__ import annotations

import time

from fastapi import HTTPException, Request

_SWEEP_INTERVAL_SECONDS = 300.0


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: float) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._last_sweep = time.monotonic()

    def _sweep(self, now: float) -> None:
        if now - self._last_sweep < _SWEEP_INTERVAL_SECONDS:
            return
        cutoff = now - self._window_seconds
        self._hits = {
            key: hits
            for key, hits in self._hits.items()
            if any(hit > cutoff for hit in hits)
        }
        self._last_sweep = now

    def __call__(self, request: Request) -> None:
        key = client_ip(request)
        now = time.monotonic()
        self._sweep(now)

        window_start = now - self._window_seconds
        hits = [hit for hit in self._hits.get(key, []) if hit > window_start]
        hits.append(now)
        self._hits[key] = hits
        if len(hits) > self._max_attempts:
            raise HTTPException(
                status_code=429,
                detail="Too many login attempts - try again in a minute",
                headers={"Retry-After": str(int(self._window_seconds))},
            )


login_rate_limiter = RateLimiter(max_attempts=5, window_seconds=60)
