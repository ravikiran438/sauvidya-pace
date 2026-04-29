# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Pydantic types for the active-augmentation profile extension to PACE.

Reference: extensions/augmentation_profile/README.md and AugmentationProfile.tla.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

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
