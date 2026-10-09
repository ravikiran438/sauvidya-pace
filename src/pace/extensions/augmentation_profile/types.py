# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Pydantic types for the active-augmentation profile extension to PACE.

Reference: extensions/augmentation_profile/README.md and AugmentationProfile.tla.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AxisKind(str, Enum):
    """The three kinds of augmentation an axis may declare."""

    COMPENSATE = "compensate"
    AMPLIFY = "amplify"
    PRESERVE = "preserve"


class Mediation(str, Enum):
    """How an action was mediated; required on every AugmentationAction (AUG-2)."""

    AGENT_COMPENSATED = "agent_compensated"
    AGENT_AMPLIFIED = "agent_amplified"
    USER_DIRECT = "user_direct"
    AGENT_HANDED_OFF = "agent_handed_off"


class AugmentationAxis(BaseModel):
    """A single named dimension of augmentation."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    name: str = Field(..., min_length=1)
    kind: AxisKind
    description: Optional[str] = None


class EmergencyTrigger(BaseModel):
    """A declared crisis condition that MUST force handoff (AUG-5)."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)


class AugmentationProfile(BaseModel):
    """Per-principal declaration of active augmentation contract."""

    model_config = ConfigDict(str_strip_whitespace=True)

    principal_id: str = Field(..., min_length=1)
    version: str = Field(
        ...,
        min_length=1,
        description=(
            "Profile version. Versions are append-only: re-declaring an "
            "axis creates a new version, and every AugmentationAction "
            "records the version it was taken under (AUG-4)."
        ),
    )
    pcp_version: str = Field(
        ...,
        min_length=1,
        description="The PrincipalCapabilityProfile version this profile binds to",
    )
    axes: List[AugmentationAxis] = Field(min_length=1)
    emergency_triggers: List[EmergencyTrigger] = Field(default_factory=list)
    identity_consent: bool = Field(
        default=False,
        description=(
            "AUG-3. Explicit consent for agent actions that alter "
            "principal's voice or written style."
        ),
    )
    declared_at: datetime
    declared_by: str = Field(
        ...,
        description="'principal' or 'guardian:<id>' (matches PCP-3)",
    )

    @model_validator(mode="after")
    def _axis_names_unique(self) -> "AugmentationProfile":
        seen: set[str] = set()
        for ax in self.axes:
            if ax.name in seen:
                raise ValueError(f"axis '{ax.name}' declared twice")
            seen.add(ax.name)
        return self

    def axis_kind(self, name: str) -> Optional[AxisKind]:
        for ax in self.axes:
            if ax.name == name:
                return ax.kind
        return None

    def trigger_names(self) -> set[str]:
        return {t.name for t in self.emergency_triggers}


class AugmentationAction(BaseModel):
    """A logged action; AUG-2 requires the mediation field on every entry."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    principal_id: str = Field(..., min_length=1)
    axis_name: str = Field(..., min_length=1)
    mediation: Mediation
    profile_version: str = Field(
        ...,
        min_length=1,
        description=(
            "AugmentationProfile version in force when the action was "
            "taken. Audits judge the action against that version (AUG-4)."
        ),
    )
    task_id: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Task the action belongs to; scopes step-ups (AUG-6).",
    )
    alters_identity: bool = Field(
        default=False,
        description=(
            "True if this action alters the principal's voice or written "
            "style (AUG-3 trigger)."
        ),
    )
    description: Optional[str] = None
    at: datetime


class AxisRevertedEvent(BaseModel):
    """Typed reversion event (AUG-1).

    Reversion MUST be a typed event recorded against the profile, not a
    soft toggle on an axis record. Once reverted, no further
    `agent_compensated` or `agent_amplified` action may target this axis.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    principal_id: str = Field(..., min_length=1)
    axis_name: str = Field(..., min_length=1)
    reverted_at: datetime
    reverted_by: str = Field(
        ...,
        description="'principal' or 'guardian:<id>'",
    )


class HandoffEvent(BaseModel):
    """Typed emergency-handoff event (AUG-5).

    Once a HandoffEvent is recorded for a principal, no further
    compensate/amplify action may be taken until the human acknowledgement
    field is populated by an authorized human operator.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    principal_id: str = Field(..., min_length=1)
    trigger_name: str = Field(..., min_length=1)
    fired_at: datetime
    human_acknowledged_at: Optional[datetime] = None
    human_acknowledged_by: Optional[str] = None


class StepUpEndReason(str, Enum):
    """Why a step-up stopped blocking agents (AUG-6).

    There is deliberately no ``expired`` reason: reaching ``expires_at``
    only makes a nudge due. Help resumes only when the task ends or the
    principal ends the step-up.
    """

    TASK_ENDED = "task_ended"
    PRINCIPAL_ENDED = "principal_ended"


class StepUpEvent(BaseModel):
    """Task-scoped step-up (AUG-6).

    The principal takes one axis back for one task: while the step-up is
    open, no agent may compensate or amplify on that axis within that
    task. The task ending closes it. ``expires_at`` is a backstop for
    abandoned tasks: once it passes, the agent nudges the principal and
    keeps waiting; it never resumes help on its own.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    principal_id: str = Field(..., min_length=1)
    axis_name: str = Field(..., min_length=1)
    task_id: str = Field(..., min_length=1)
    granted_by: Literal["principal"] = Field(
        default="principal",
        description=(
            "Only the principal may step up. A guardian stepping a "
            "principal up would withhold help on their behalf."
        ),
    )
    granted_at: datetime
    expires_at: datetime = Field(
        ...,
        description="After this time a nudge is due if the step-up is still open.",
    )
    nudged_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    end_reason: Optional[StepUpEndReason] = None

    @model_validator(mode="after")
    def _coherent_timeline(self) -> "StepUpEvent":
        if self.expires_at <= self.granted_at:
            raise ValueError("expires_at must be after granted_at")
        if (self.ended_at is None) != (self.end_reason is None):
            raise ValueError("ended_at and end_reason must be set together")
        if self.ended_at is not None and self.ended_at < self.granted_at:
            raise ValueError("ended_at must not precede granted_at")
        if self.nudged_at is not None:
            if self.nudged_at < self.expires_at:
                raise ValueError("nudged_at must not precede expires_at")
            if self.ended_at is not None and self.nudged_at > self.ended_at:
                raise ValueError("nudged_at must not follow ended_at")
        return self

    def blocks_at(self, when: datetime) -> bool:
        """True if agents must stay off this axis in this task at ``when``.

        Passing ``expires_at`` does not unblock: only ``ended_at`` does.
        """
        if when < self.granted_at:
            return False
        return self.ended_at is None or when < self.ended_at

    def nudge_due(self, now: datetime) -> bool:
        """True if the time limit has passed, the step-up is still open,
        and the principal has not been nudged yet."""
        return (
            now >= self.expires_at
            and self.ended_at is None
            and self.nudged_at is None
        )
