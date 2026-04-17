# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""AIC-1 (time window) and AIC-2 (option count) validators."""

from __future__ import annotations

from pace.types.adaptive_interaction_contract import (
    AdaptiveInteractionContract,
    TimeWindow,
)


class TimeWindowViolationError(ValueError):
    """AIC-1: Interaction initiated outside valid time windows."""


class OptionOverloadError(ValueError):
    """AIC-2: More than max_options_per_turn presented."""


def _time_to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _in_window(current_hhmm: str, window: TimeWindow) -> bool:
    current = _time_to_minutes(current_hhmm)
    start = _time_to_minutes(window.start)
    end = _time_to_minutes(window.end)
    if start <= end:
        return start <= current <= end
    # Wraps midnight
    return current >= start or current <= end


def validate_time_window(
    contract: AdaptiveInteractionContract,
    current_time_hhmm: str,
    is_emergency: bool = False,
) -> None:
    """AIC-1: No interaction outside valid_time_windows unless emergency.
    Also checks sundown_block."""
    if is_emergency:
        return

    rules = contract.interaction_rules

    # Check sundown block first
    if rules.sundown_block is not None:
        if _in_window(current_time_hhmm, rules.sundown_block):
            raise TimeWindowViolationError(
                f"AIC-1 violated: current time {current_time_hhmm} falls within "
                f"sundown block ({rules.sundown_block.start}-{rules.sundown_block.end}) "
                f"for principal {contract.principal_id!r}"
            )

    # Check valid time windows
    if rules.valid_time_windows:
        in_any = any(
            _in_window(current_time_hhmm, w) for w in rules.valid_time_windows
        )
        if not in_any:
            windows_str = ", ".join(
                f"{w.start}-{w.end}" for w in rules.valid_time_windows
            )
            raise TimeWindowViolationError(
                f"AIC-1 violated: current time {current_time_hhmm} is outside "
                f"all valid windows ({windows_str}) for principal "
                f"{contract.principal_id!r}"
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
