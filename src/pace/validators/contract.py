# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""AIC-1 (time window) and AIC-2 (option count) validators."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
from zoneinfo import ZoneInfo

from pace.types.adaptive_interaction_contract import (
    AdaptiveInteractionContract,
    TimeWindow,
)
from pace.types.interaction_modality import InteractionModality


class ModalityContractError(ValueError):
    """AIC-5: an InteractionModality steps outside the contract it was
    computed under. ``problems`` lists each violation."""

    def __init__(self, message: str, problems: list[str] | None = None):
        super().__init__(message)
        self.problems = list(problems or [])


class DailyLimitError(ValueError):
    """AIC-1: the principal has already been contacted the contract's
    maximum number of times today."""


class RetryViolationError(ValueError):
    """AIC-3: a retry breaks the contract's non-response policy."""


class TimeWindowViolationError(ValueError):
    """AIC-1: Interaction initiated outside valid time windows."""


class OptionOverloadError(ValueError):
    """AIC-2: More than max_options_per_turn presented."""


def _time_to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _in_window(current: int, window: TimeWindow) -> bool:
    start = _time_to_minutes(window.start)
    end = _time_to_minutes(window.end)
    if start <= end:
        return start <= current <= end
    # Wraps midnight
    return current >= start or current <= end


def principal_local_time(
    contract: AdaptiveInteractionContract, at: datetime
) -> datetime:
    """``at`` in the principal's time zone. ``at`` must carry its own zone:
    a naive timestamp cannot say whose clock it was read from."""
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError(
            "AIC-1 needs a zone-aware timestamp; a naive time is ambiguous "
            "between the agent's clock and the principal's"
        )
    return at.astimezone(ZoneInfo(contract.interaction_rules.timezone))


def validate_time_window(
    contract: AdaptiveInteractionContract,
    at: datetime,
    is_emergency: bool = False,
) -> None:
    """AIC-1: No interaction outside valid_time_windows unless emergency.
    Also checks sundown_block.

    Windows are the principal's local times (``interaction_rules.timezone``).
    ``at`` is converted to that zone first, so an agent in another country,
    or on the other side of a daylight-saving change, is judged by her clock.
    """
    if is_emergency:
        return

    rules = contract.interaction_rules
    local = principal_local_time(contract, at)
    current = local.hour * 60 + local.minute
    stamp = (
        f"{local:%H:%M} {rules.timezone} "
        f"({at.isoformat(timespec='minutes')} on the agent's clock)"
    )

    # Check sundown block first
    if rules.sundown_block is not None:
        if _in_window(current, rules.sundown_block):
            raise TimeWindowViolationError(
                f"AIC-1 violated: {stamp} falls within the sundown block "
                f"({rules.sundown_block.start}-{rules.sundown_block.end}) "
                f"for principal {contract.principal_id!r}"
            )

    # Check valid time windows
    if rules.valid_time_windows:
        in_any = any(_in_window(current, w) for w in rules.valid_time_windows)
        if not in_any:
            windows_str = ", ".join(
                f"{w.start}-{w.end}" for w in rules.valid_time_windows
            )
            raise TimeWindowViolationError(
                f"AIC-1 violated: {stamp} is outside all valid windows "
                f"({windows_str}) for principal {contract.principal_id!r}"
            )


def validate_option_count(
    contract: AdaptiveInteractionContract,
    options_presented: int,
) -> None:
    """AIC-2: No more than max_options_per_turn in a single interaction turn."""
    max_opts = contract.interaction_rules.max_options_per_turn
    if options_presented > max_opts:
        raise OptionOverloadError(
            f"AIC-2 violated: {options_presented} options presented to principal "
            f"{contract.principal_id!r}, maximum is {max_opts}"
        )


_DENSITY = {"low": 0, "medium": 1, "high": 2}


def validate_modality_contract(
    modality: InteractionModality,
    contract: AdaptiveInteractionContract,
) -> None:
    """AIC-5: an agent's InteractionModality stays within its contract.

    Each primitive validates on its own; this checks the two together. The
    plan must be for the contract's principal and PCP version, speak the
    contract's language, wait at least as long, speak no faster, present
    no more options, carry no more information per turn, confirm the way
    the contract says, and recap prior context when the contract asks.
    Every violation is reported, not only the first.
    """
    rules = contract.interaction_rules
    plan = modality.modality_plan
    problems: list[str] = []

    if modality.principal_id != contract.principal_id:
        problems.append(
            f"modality is for principal {modality.principal_id!r}, contract "
            f"for {contract.principal_id!r}"
        )
    if modality.pcp_version != contract.pcp_version:
        problems.append(
            f"modality computed from PCP {modality.pcp_version!r}, contract "
            f"bound to {contract.pcp_version!r}"
        )
    if plan.language != rules.language:
        problems.append(
            f"language {plan.language!r}, contract binds {rules.language!r}"
        )
    if plan.timeout_seconds < rules.response_timeout_seconds:
        problems.append(
            f"waits {plan.timeout_seconds}s for a response, contract requires "
            f"at least {rules.response_timeout_seconds}s"
        )
    if plan.speech_rate > rules.speech_rate:
        problems.append(
            f"speech rate {plan.speech_rate}, contract allows at most "
            f"{rules.speech_rate}"
        )
    if plan.max_options > rules.max_options_per_turn:
        problems.append(
            f"up to {plan.max_options} options per turn, contract allows "
            f"{rules.max_options_per_turn}"
        )
    plan_density = _DENSITY.get(plan.information_density)
    rule_density = _DENSITY.get(rules.information_density)
    if plan_density is None or rule_density is None:
        problems.append(
            f"information density must be one of {sorted(_DENSITY)}, got "
            f"{plan.information_density!r} and {rules.information_density!r}"
        )
    elif plan_density > rule_density:
        problems.append(
            f"information density {plan.information_density!r}, contract "
            f"allows {rules.information_density!r}"
        )
    if plan.confirmation_style != rules.confirmation_style:
        problems.append(
            f"confirmation style {plan.confirmation_style!r}, contract "
            f"requires {rules.confirmation_style!r}"
        )
    if rules.memory_aid and not plan.memory_aid:
        problems.append("no memory recap, contract requires one each interaction")

    if problems:
        raise ModalityContractError(
            f"AIC-5 violated: InteractionModality of agent "
            f"{modality.agent_id!r} for {modality.principal_id!r} steps "
            "outside its contract: " + "; ".join(problems),
            problems,
        )


@dataclass(frozen=True)
class ContactAttempt:
    """One earlier attempt to reach the principal for the same request."""

    at: datetime
    responded: bool


def _window_key(contract: AdaptiveInteractionContract, moment: datetime):
    """(her local date, window start) for the valid window containing
    ``moment``, or None outside every window."""
    local = principal_local_time(contract, moment)
    current = local.hour * 60 + local.minute
    for window in contract.interaction_rules.valid_time_windows:
        if _in_window(current, window):
            return (local.date(), window.start)
    return None


def validate_retry(
    contract: AdaptiveInteractionContract,
    prior_attempts: Sequence[ContactAttempt],
    at: datetime,
) -> None:
    """AIC-3: may the agent try again at ``at``, after ``prior_attempts``?

    Counts non-responses since the last answered attempt. Raises if the
    escalation threshold is reached (escalate instead) or if ``at`` falls
    in the same window as the last unanswered attempt. Retries cannot run
    out first: ``NonResponsePolicy`` requires
    ``escalate_after <= max_retries + 1``.
    """
    policy = contract.interaction_rules.non_response_policy
    unanswered: list[ContactAttempt] = []
    for attempt in sorted(prior_attempts, key=lambda a: a.at):
        unanswered = [] if attempt.responded else unanswered + [attempt]
    if not unanswered:
        return

    misses = len(unanswered)
    if misses >= policy.escalate_after:
        raise RetryViolationError(
            f"AIC-3 violated: {misses} unanswered attempts to reach "
            f"{contract.principal_id!r}; escalate to the guardian instead of "
            f"contacting her again (escalate_after={policy.escalate_after})"
        )
    last = unanswered[-1]
    last_key = _window_key(contract, last.at)
    if last_key is not None and _window_key(contract, at) == last_key:
        local = principal_local_time(contract, at)
        raise RetryViolationError(
            f"AIC-3 violated: retry at {local:%H:%M} {contract.interaction_rules.timezone} "
            f"is in the same window ({last_key[1]}) as the unanswered attempt; "
            "wait for the next valid window"
        )


def _her_day(contract: AdaptiveInteractionContract, moment: datetime):
    return principal_local_time(contract, moment).date()


def interactions_remaining(
    contract: AdaptiveInteractionContract,
    prior_contacts: Sequence[ContactAttempt],
    at: datetime,
) -> int:
    """How many more contacts the principal may receive today.

    The counting unit is the principal, across every agent, by her local
    calendar day. Every agent-initiated contact counts, answered or not: an
    unanswered call still rang.
    """
    today = _her_day(contract, at)
    used = sum(1 for c in prior_contacts if _her_day(contract, c.at) == today)
    return max(0, contract.interaction_rules.max_interactions_per_day - used)


def validate_daily_limit(
    contract: AdaptiveInteractionContract,
    prior_contacts: Sequence[ContactAttempt],
    at: datetime,
    is_emergency: bool = False,
) -> None:
    """AIC-1, daily limit: no more than ``max_interactions_per_day`` contacts
    on her local calendar day, from all agents together. Emergencies are
    never blocked, but they are counted like any other contact.
    """
    if is_emergency:
        return
    if interactions_remaining(contract, prior_contacts, at) == 0:
        limit = contract.interaction_rules.max_interactions_per_day
        local = principal_local_time(contract, at)
        raise DailyLimitError(
            f"AIC-1 violated: {contract.principal_id!r} has already been "
            f"contacted {limit} time(s) on {local:%a %d %b} "
            f"({contract.interaction_rules.timezone}), the contract's daily "
            "limit across all agents; wait until tomorrow her time"
        )
