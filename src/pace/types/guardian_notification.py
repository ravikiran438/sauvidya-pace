# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""GuardianNotification: what a guardian receives when an agent breaks the
contract (AIC-4, ``notify_guardian``).

Written for a person who has five minutes and no logs: which agent, which
rule, what happened in plain words, what was done about it, when it
happened on both clocks, and what happens next. It carries no capacity
data (CCC-2): unknown fields are rejected, so a capacity signal cannot be
attached by accident.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pace.types.violation_notice import EnforcementAction, ViolationType


class GuardianNotification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    notification_id: str = Field(..., min_length=1)
    principal_id: str = Field(..., min_length=1)
    guardian_id: Optional[str] = Field(
        default=None, description="The approving guardian, when the contract names one."
    )
    agent_id: str = Field(..., min_length=1, description="The agent that broke the contract.")
    rule: str = Field(..., description="The invariant broken, e.g. 'AIC-1'.")
    violation_type: ViolationType
    summary: str = Field(..., min_length=1, description="What happened, in plain words.")
    occurred_at: datetime = Field(..., description="When it happened, zone-aware.")
    principal_local_time: str = Field(
        ..., description="When it happened on the principal's clock, with her zone."
    )
    guardian_local_time: Optional[str] = Field(
        default=None,
        description="When it happened on the guardian's clock, when the orchestrator knows it.",
    )
    actions_taken: list[EnforcementAction] = Field(..., min_length=1)
    next_step: Optional[str] = Field(
        default=None, description="What happens next without the guardian doing anything."
    )

    @field_validator("occurred_at")
    @classmethod
    def _zone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be zone-aware")
        return value
