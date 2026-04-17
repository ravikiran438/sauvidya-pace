# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""AdaptiveInteractionContract: binding rules for all agents interacting with a principal (paper Section 3.4).

Invariant AIC-1: No interaction outside valid_time_windows (unless emergency).
Invariant AIC-2: No more than max_options_per_turn per interaction turn.
Invariant AIC-3: Non-response -> wait for next window, not immediate retry.
Invariant AIC-4: Violations trigger violation_policy automatically.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TimeWindow(BaseModel):
    model_config = ConfigDict(frozen=True)
    start: str = Field(..., description="HH:MM format")
    end: str = Field(..., description="HH:MM format")


class ViolationPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)
    on_time_window_violation: str = Field(default="block_agent + notify_guardian")
    on_option_overload: str = Field(default="reject_interaction + log")
    on_language_mismatch: str = Field(default="reject_interaction + escalate")
    on_capacity_check_skip: str = Field(default="block_agent + notify_guardian + audit_flag")


class InteractionRules(BaseModel):
    model_config = ConfigDict(frozen=True)

    response_timeout_seconds: int = Field(default=300, gt=0)
    max_options_per_turn: int = Field(default=2, gt=0)
    confirmation_style: str = Field(default="voice_repeat_back")
    language: str = Field(..., description="ISO 639-1 code")
    speech_rate: float = Field(default=0.7, gt=0.0, le=1.0)
    information_density: str = Field(default="low")
    memory_aid: bool = Field(default=True)
    guardian_cc: str = Field(default="always", description="always | threshold | never")
    valid_time_windows: List[TimeWindow] = Field(default_factory=list)
    sundown_block: Optional[TimeWindow] = Field(default=None)
    max_interactions_per_day: int = Field(default=3, gt=0)
    escalation_on_confusion: bool = Field(default=True)


class AdaptiveInteractionContract(BaseModel):
    """Binding agreement governing how all agents interact with this principal."""

    model_config = ConfigDict(str_strip_whitespace=True)

    principal_id: str
    pcp_version: str
    guardian_approved_by: Optional[str] = Field(default=None)
    interaction_rules: InteractionRules
    violation_policy: ViolationPolicy = Field(default_factory=ViolationPolicy)
