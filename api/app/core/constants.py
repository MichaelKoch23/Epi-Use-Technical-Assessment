"""Thresholds shared by the analytics repository/service/router (§ analytics)
so they live in one place rather than being scattered through query code."""

from __future__ import annotations

WIDE_SPAN_THRESHOLD = 10  # more than this many direct reports is flagged
DEEP_CHAIN_THRESHOLD = 6  # depth at or beyond this is flagged
ANOMALY_LIST_LIMIT = 20  # cap each anomaly list
