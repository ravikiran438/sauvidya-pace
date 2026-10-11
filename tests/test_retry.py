# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""AIC-3: non-response policy."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from pace.types import (
    AdaptiveInteractionContract,
    InteractionRules,
    NonResponsePolicy,
    TimeWindow,
)
from pace.validators import ContactAttempt, RetryViolationError, validate_retry

IST = ZoneInfo("Asia/Kolkata")


def _contract(policy: NonResponsePolicy | None = None) -> AdaptiveInteractionContract:
    return AdaptiveInteractionContract(
        principal_id="Lakshmi",
        pcp_version="v1",
        interaction_rules=InteractionRules(
            language="te",
            timezone="Asia/Kolkata",
            valid_time_windows=[
                TimeWindow(start="09:00", end="11:00"),
                TimeWindow(start="14:00", end="16:00"),
            ],
            sundown_block=TimeWindow(start="17:00", end="08:00"),
            non_response_policy=policy or NonResponsePolicy(),
        ),
    )


def _t(h: int, m: int, day: int = 10) -> datetime:
    return datetime(2026, 10, day, h, m, tzinfo=IST)


def test_story_from_consumer_md():
    """No answer at 10:15: no retry at 10:20, one at 14:00, then escalate."""
    first = [ContactAttempt(_t(10, 15), responded=False)]
    with pytest.raises(RetryViolationError, match="same window"):
        validate_retry(_contract(), first, _t(10, 20))
    validate_retry(_contract(), first, _t(14, 0))
    second = first + [ContactAttempt(_t(14, 0), responded=False)]
    with pytest.raises(RetryViolationError, match="escalate to the guardian"):
        validate_retry(_contract(), second, _t(14, 5))


def test_first_contact_is_not_a_retry():
    validate_retry(_contract(), [], _t(10, 0))


def test_an_answer_resets_the_count():
    history = [
        ContactAttempt(_t(9, 30), responded=False),
        ContactAttempt(_t(14, 0), responded=True),
    ]
    validate_retry(_contract(), history, _t(14, 30))


def test_same_window_next_day_is_a_new_window():
    first = [ContactAttempt(_t(10, 15), responded=False)]
    validate_retry(_contract(), first, _t(10, 15, day=11))


def test_policy_that_could_drop_her_silently_is_rejected():
    with pytest.raises(ValidationError, match="dropped silently"):
        NonResponsePolicy(max_retries=1, escalate_after=3)


@pytest.mark.parametrize("max_retries", range(0, 5))
def test_escalation_always_comes_before_retries_run_out(max_retries):
    """For every valid policy, unanswered attempts in successive windows end
    in escalation, never in an exhausted retry budget."""
    for escalate_after in range(1, max_retries + 2):
        contract = _contract(NonResponsePolicy(max_retries=max_retries, escalate_after=escalate_after))
        history: list[ContactAttempt] = []
        moment = _t(9, 30)
        while True:
            try:
                validate_retry(contract, history, moment)
            except RetryViolationError as err:
                assert "escalate to the guardian" in str(err)
                break
            history.append(ContactAttempt(moment, responded=False))
            moment += timedelta(days=1)
        assert len(history) == escalate_after
        assert len(history) - 1 <= max_retries


def test_naive_retry_time_rejected():
    first = [ContactAttempt(_t(10, 15), responded=False)]
    with pytest.raises(ValueError, match="zone-aware"):
        validate_retry(_contract(), first, datetime(2026, 10, 10, 14, 0))
