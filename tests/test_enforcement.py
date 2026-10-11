# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""AIC-4: violation policy actions and the guardian notification."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from pace.types import (
    AdaptiveInteractionContract,
    EnforcementAction,
    GuardianNotification,
    InteractionRules,
    TimeWindow,
    ViolationPolicy,
    ViolationType,
)
from pace.validators import enforce_violation, next_window_start

CHICAGO = ZoneInfo("America/Chicago")
IST = ZoneInfo("Asia/Kolkata")


def _contract(policy: ViolationPolicy | None = None) -> AdaptiveInteractionContract:
    return AdaptiveInteractionContract(
        principal_id="Lakshmi",
        pcp_version="v1",
        guardian_approved_by="guardian:ravi",
        interaction_rules=InteractionRules(
            language="te",
            timezone="Asia/Kolkata",
            valid_time_windows=[
                TimeWindow(start="09:00", end="11:00"),
                TimeWindow(start="14:00", end="16:00"),
            ],
            sundown_block=TimeWindow(start="17:00", end="08:00"),
        ),
        violation_policy=policy or ViolationPolicy(),
    )


def test_guardian_story_from_consumer_md():
    """An agent in Texas calls at 08:10 CDT, 18:40 in Hyderabad."""
    decision = enforce_violation(
        _contract(),
        ViolationType.TIME_WINDOW,
        "booking-agent",
        datetime(2026, 10, 10, 8, 10, tzinfo=CHICAGO),
        guardian_timezone="America/Chicago",
    )
    note = decision.notification
    assert decision.rule == "AIC-1"
    assert decision.broadcast_block is True
    assert note.principal_local_time == "18:40 IST (Sat 10 Oct)"
    assert note.guardian_local_time == "08:10 CDT (Sat 10 Oct)"
    assert note.next_step == "Agents may contact her again from 09:00 IST (Sun 11 Oct), her time."
    assert note.agent_id == "booking-agent"
    assert note.guardian_id == "guardian:ravi"
    assert "the agent was blocked" in note.summary


def test_policy_without_notify_sends_nothing():
    decision = enforce_violation(
        _contract(), "option_overload", "a1", datetime(2026, 10, 10, 10, 0, tzinfo=IST)
    )
    assert decision.actions == (EnforcementAction.REJECT_INTERACTION, EnforcementAction.LOG)
    assert decision.notification is None
    assert decision.broadcast_block is False


def test_language_mismatch_escalates():
    decision = enforce_violation(
        _contract(), "language_mismatch", "a1", datetime(2026, 10, 10, 10, 0, tzinfo=IST)
    )
    assert decision.escalate is True and decision.rule == "IM-2"


def test_capacity_check_skip_notifies_and_audits():
    decision = enforce_violation(
        _contract(), "capacity_check_skip", "a1", datetime(2026, 10, 10, 10, 0, tzinfo=IST)
    )
    assert EnforcementAction.AUDIT_FLAG in decision.actions
    assert decision.notification.rule == "CCC-1"
    assert decision.notification.next_step is None


def test_paper_string_form_accepted():
    policy = ViolationPolicy(on_option_overload="reject_interaction + notify_guardian")
    decision = enforce_violation(
        _contract(policy), "option_overload", "a1", datetime(2026, 10, 10, 10, 0, tzinfo=IST)
    )
    assert decision.notification is not None


def test_unknown_action_rejected():
    with pytest.raises(ValidationError):
        ViolationPolicy(on_option_overload="reject_interaction + call_the_police")


def test_notification_cannot_carry_capacity_data():
    """CCC-2: unknown fields are rejected, so no capacity signal can ride along."""
    note = enforce_violation(
        _contract(), "time_window", "a1", datetime(2026, 10, 10, 8, 10, tzinfo=CHICAGO)
    ).notification
    with pytest.raises(ValidationError):
        GuardianNotification(**note.model_dump(), capacity_signal=0.31)
    assert "capacity" not in note.summary


def test_notification_requires_zone_aware_time():
    note = enforce_violation(
        _contract(), "time_window", "a1", datetime(2026, 10, 10, 8, 10, tzinfo=CHICAGO)
    ).notification
    data = note.model_dump()
    data["occurred_at"] = datetime(2026, 10, 10, 8, 10)
    with pytest.raises(ValidationError, match="zone-aware"):
        GuardianNotification(**data)


@pytest.mark.parametrize(
    "local, expected",
    [
        ("06:30", "09:00"),   # in sundown, morning window today
        ("12:00", "14:00"),   # between windows
        ("16:30", "09:00"),   # after the last window: tomorrow
    ],
)
def test_next_window_start(local, expected):
    h, m = map(int, local.split(":"))
    nxt = next_window_start(_contract(), datetime(2026, 10, 10, h, m, tzinfo=IST))
    assert nxt.strftime("%H:%M") == expected
