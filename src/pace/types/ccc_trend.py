# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""CCCTrend: longitudinal direction of capacity_signal samples.

``CCCTrend`` is the **canonical wire-format enum** describing the
direction of a principal's capacity_signal over time. The four values
(STABLE, IMPROVING, DECLINING, INSUFFICIENT_DATA) are normative — any
PACE deployment that reports a trend MUST pick one of them.

``derive_ccc_trend`` is a **reference implementation** of one
reasonable derivation (least-squares slope over the trailing window).
It is NOT normative: deployments are free to use a different statistic
(EWMA, Mann-Kendall, etc.) so long as they map their result onto the
canonical four-value enum. This function exists so deployments without
a strong opinion get a sensible default; teams with statistical
expertise should plug in their own.

Reference algorithm:

  * Take all CCC samples whose ``timestamp`` falls inside the trailing
    ``window_days`` from "now".
  * If fewer than ``min_samples`` (default 5) fall in the window:
    INSUFFICIENT_DATA.
  * Otherwise, compute the OLS slope of ``capacity_signal`` against
    sample-index (treating samples as equally-spaced is a deliberate
    simplification).
  * Slope < -SLOPE_NOISE_FLOOR (default 0.005): DECLINING
  * Slope >  SLOPE_NOISE_FLOOR                : IMPROVING
  * |slope| <= SLOPE_NOISE_FLOOR              : STABLE
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Sequence

from pace.types.consent_capacity_check import ConsentCapacityCheck


SLOPE_NOISE_FLOOR = 0.005
DEFAULT_WINDOW_DAYS = 30
DEFAULT_MIN_SAMPLES = 5


class CCCTrend(str, Enum):
    """Direction of capacity_signal over the configured trend window."""

    STABLE = "stable"
    IMPROVING = "improving"
    DECLINING = "declining"
    INSUFFICIENT_DATA = "insufficient_data"


def _parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)


def derive_ccc_trend(
    samples: Sequence[ConsentCapacityCheck],
    *,
    now: datetime | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    slope_noise_floor: float = SLOPE_NOISE_FLOOR,
) -> CCCTrend:
    """Classify the trend of capacity_signal in the trailing ``window_days``.

    Pure function: ``samples`` is consumed read-only and ``now`` is
    optional (defaults to current UTC) so tests can be deterministic.
    """
    if window_days <= 0:
        raise ValueError("window_days must be positive")
    if min_samples < 2:
        raise ValueError("min_samples must be >= 2")

    now_utc = now or datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=window_days)

    in_window: list[ConsentCapacityCheck] = []
    for s in samples:
        if _parse_iso(s.timestamp) >= cutoff:
            in_window.append(s)

    if len(in_window) < min_samples:
        return CCCTrend.INSUFFICIENT_DATA

    # Order chronologically so the slope sign means time-direction.
    in_window.sort(key=lambda s: _parse_iso(s.timestamp))

    n = len(in_window)
    xs = list(range(n))
    ys = [s.capacity_signal for s in in_window]

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return CCCTrend.STABLE
    slope = num / den

    if slope > slope_noise_floor:
        return CCCTrend.IMPROVING
    if slope < -slope_noise_floor:
        return CCCTrend.DECLINING
    return CCCTrend.STABLE
