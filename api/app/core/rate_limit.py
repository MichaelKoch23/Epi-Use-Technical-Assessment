"""Rate limiting for authentication endpoints (§9.4 - "blunt credential
stuffing"). A sliding-window counter per client IP, in-process.

In-process is the one real limitation worth stating plainly: this blunts
a single attacker hammering a single instance, but doesn't share state
across Cloud Run instances the way the reporting-cycle invariant's
deferred trigger does at the database layer. A shared store (Redis) is
the upgrade path if this ever needs to hold under multi-instance scale.
"""

from __future__ import annotations

import time

from fastapi import HTTPException, Request

# Buckets idle for longer than this are dropped on the next sweep. Without
# it, `_hits` keeps one list per source IP for the process's whole life -
# an unbounded, attacker-controlled dict, which is a memory-exhaustion
# vector in the component whose entire job is to resist abuse.
_SWEEP_INTERVAL_SECONDS = 300.0


def client_ip(request: Request) -> str:
    """The caller's address, as seen through the deployment's proxy.

    On Cloud Run (and behind any load balancer) the socket peer is the
    ingress proxy, so `request.client.host` is the *same value for every
    caller*. Keying the limiter on it would bucket the entire internet
    together: five failed logins from anyone locks out everyone, and no
    individual attacker is ever limited. Uvicorn is started with
    `--proxy-headers`, which rewrites `request.client` from the
    left-most `X-Forwarded-For` entry; this helper is the single place
    that decision is read, and it falls back to the raw peer when the app
    is run without a proxy in front of it.
    """
    return request.client.host if request.client else "unknown"


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: float) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        # Not a defaultdict: a lookup for an unknown key must not create a
        # bucket, or merely observing the limiter would grow it.
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
