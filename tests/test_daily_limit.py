# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""AIC-1 daily limit: per principal, across agents, by her local day."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from pace.types import AdaptiveInteractionContract, InteractionRules
from pace.validators import (
    ContactAttempt,
    DailyLimitError,
    interactions_remaining,
    validate_daily_limit,
)

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


def _contract(limit: int = 3) -> AdaptiveInteractionContract:
    return AdaptiveInteractionContract(
        principal_id="Lakshmi",
        pcp_version="v1",
        interaction_rules=InteractionRules(
            language="te", timezone="Asia/Kolkata", max_interactions_per_day=limit
        ),
    )


def _ist(day: int, h: int, m: int = 0) -> datetime:
    return datetime(2026, 10, day, h, m, tzinfo=IST)


def test_three_agents_one_call_each_is_three_calls_to_her():
    """The counting unit is her, not the agent."""
    calls = [
        ContactAttempt(_ist(10, 9, 15), responded=True),   # booking agent
        ContactAttempt(_ist(10, 10, 30), responded=True),  # pharmacy agent
        ContactAttempt(_ist(10, 14, 10), responded=True),  # insurance agent
    ]
    assert interactions_remaining(_contract(), calls, _ist(10, 15)) == 0
    with pytest.raises(DailyLimitError, match="3 time"):
        validate_daily_limit(_contract(), calls, _ist(10, 15))


def test_unanswered_calls_count():
    calls = [ContactAttempt(_ist(10, h), responded=False) for h in (9, 10, 14)]
    with pytest.raises(DailyLimitError):
        validate_daily_limit(_contract(), calls, _ist(10, 15))


def test_new_day_on_her_clock_resets():
    calls = [ContactAttempt(_ist(10, h), responded=True) for h in (9, 10, 14)]
    validate_daily_limit(_contract(), calls, _ist(11, 9))
    assert interactions_remaining(_contract(), calls, _ist(11, 9)) == 3


def test_utc_day_would_count_the_wrong_calls():
    """At 05:00 IST on the 11th it is still the 10th in UTC. Counting by UTC
    day would block her first contact of the day with yesterday's calls."""
    calls = [ContactAttempt(_ist(10, h), responded=True) for h in (9, 10, 14)]
    early = _ist(11, 5)
    assert early.astimezone(UTC).day == 10
    validate_daily_limit(_contract(), calls, early)


def test_emergency_never_blocked_but_counted():
    calls = [ContactAttempt(_ist(10, h), responded=True) for h in (9, 10, 14)]
    validate_daily_limit(_contract(), calls, _ist(10, 15), is_emergency=True)
    with_emergency = calls[:2] + [ContactAttempt(_ist(10, 12), responded=True)]
    assert interactions_remaining(_contract(), with_emergency, _ist(10, 15)) == 0


def test_naive_time_rejected():
    with pytest.raises(ValueError, match="zone-aware"):
        validate_daily_limit(_contract(), [], datetime(2026, 10, 10, 9, 0))
