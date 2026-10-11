# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""AIC-4 enforcement: turn a detected violation into the contract's actions.

``enforce_violation`` reads the contract's ``violation_policy`` for the kind
of violation and returns what to do: the actions, whether to broadcast a
block to peer orchestrators, and, when the policy says ``notify_guardian``,
a ready-to-send ``GuardianNotification``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from pace.types.adaptive_interaction_contract import AdaptiveInteractionContract
from pace.types.guardian_notification import GuardianNotification
from pace.types.violation_notice import EnforcementAction, ViolationType
from pace.validators.contract import principal_local_time, _in_window, _time_to_minutes

_POLICY_FIELD = {
    ViolationType.TIME_WINDOW: "on_time_window_violation",
    ViolationType.OPTION_OVERLOAD: "on_option_overload",
    ViolationType.LANGUAGE_MISMATCH: "on_language_mismatch",
    ViolationType.CAPACITY_CHECK_SKIP: "on_capacity_check_skip",
    ViolationType.MODALITY_CONTRACT: "on_modality_contract_violation",
}

RULE = {
    ViolationType.TIME_WINDOW: "AIC-1",
    ViolationType.OPTION_OVERLOAD: "AIC-2",
    ViolationType.LANGUAGE_MISMATCH: "IM-2",
    ViolationType.CAPACITY_CHECK_SKIP: "CCC-1",
    ViolationType.MODALITY_CONTRACT: "AIC-5",
}

_SUMMARY = {
    ViolationType.TIME_WINDOW: "An agent tried to contact {p} outside the hours her contract allows.",
    ViolationType.OPTION_OVERLOAD: "An agent offered {p} more choices at once than her contract allows.",
    ViolationType.LANGUAGE_MISMATCH: "An agent tried to talk to {p} in a language she cannot follow.",
    ViolationType.CAPACITY_CHECK_SKIP: "An agent tried to record consent from {p} without first checking she could give it.",
    ViolationType.MODALITY_CONTRACT: "An agent planned to talk to {p} in a way her contract does not allow.",
}

_ACTION_WORDS = {
    EnforcementAction.BLOCK_AGENT: "the agent was blocked",
    EnforcementAction.REJECT_INTERACTION: "the contact was stopped",
    EnforcementAction.NOTIFY_GUARDIAN: "you were notified",
    EnforcementAction.AUDIT_FLAG: "it was flagged for audit",
    EnforcementAction.ESCALATE: "it was escalated",
    EnforcementAction.LOG: "it was logged",
}


@dataclass(frozen=True)
class EnforcementDecision:
    violation_type: ViolationType
    rule: str
    actions: tuple[EnforcementAction, ...]
    broadcast_block: bool
    escalate: bool
    notification: Optional[GuardianNotification]


def _clock(moment: datetime) -> str:
    return f"{moment:%H:%M} {moment.tzname()} ({moment:%a %d %b})"


def next_window_start(
    contract: AdaptiveInteractionContract, at: datetime
) -> Optional[datetime]:
    """The next moment, in the principal's zone, when contact is allowed:
    the start of the next valid window outside the sundown block. None if
    the contract has no windows."""
    rules = contract.interaction_rules
    local = principal_local_time(contract, at)
    zone = ZoneInfo(rules.timezone)
    starts = sorted(_time_to_minutes(w.start) for w in rules.valid_time_windows)
    for day in range(8):
        date = (local + timedelta(days=day)).date()
        for minutes in starts:
            candidate = datetime(
                date.year, date.month, date.day, minutes // 60, minutes % 60, tzinfo=zone
            )
            if candidate <= local:
                continue
            if rules.sundown_block and _in_window(minutes, rules.sundown_block):
                continue
            return candidate
    return None


def enforce_violation(
    contract: AdaptiveInteractionContract,
    violation_type: ViolationType,
    agent_id: str,
    at: datetime,
    *,
    detail: Optional[str] = None,
    guardian_timezone: Optional[str] = None,
    notification_id: Optional[str] = None,
) -> EnforcementDecision:
    """AIC-4: apply the contract's violation policy to one violation.

    ``at`` is when the violation happened (zone-aware). ``guardian_timezone``
    lets the notification show the guardian's own clock as well as hers.
    """
    violation_type = ViolationType(violation_type)
    actions = tuple(getattr(contract.violation_policy, _POLICY_FIELD[violation_type]))
    rule = RULE[violation_type]
    notification = None

    if EnforcementAction.NOTIFY_GUARDIAN in actions:
        local = principal_local_time(contract, at)
        summary = _SUMMARY[violation_type].format(p=contract.principal_id)
        if detail:
            summary = f"{summary} {detail}"
        done = ", ".join(_ACTION_WORDS[a] for a in actions)
        summary = f"{summary} What happened next: {done}."
        next_step = None
        if violation_type == ViolationType.TIME_WINDOW:
            nxt = next_window_start(contract, at)
            if nxt is not None:
                next_step = f"Agents may contact her again from {_clock(nxt)}, her time."
        notification = GuardianNotification(
            notification_id=notification_id or str(uuid.uuid4()),
            principal_id=contract.principal_id,
            guardian_id=contract.guardian_approved_by,
            agent_id=agent_id,
            rule=rule,
            violation_type=violation_type,
            summary=summary,
            occurred_at=at,
            principal_local_time=_clock(local),
            guardian_local_time=(
                _clock(at.astimezone(ZoneInfo(guardian_timezone)))
                if guardian_timezone
                else None
            ),
            actions_taken=list(actions),
            next_step=next_step,
        )

    return EnforcementDecision(
        violation_type=violation_type,
        rule=rule,
        actions=actions,
        broadcast_block=EnforcementAction.BLOCK_AGENT in actions,
        escalate=EnforcementAction.ESCALATE in actions,
        notification=notification,
    )
