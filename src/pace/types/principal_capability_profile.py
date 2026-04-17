# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""PrincipalCapabilityProfile: per-principal, on-device capability declaration (paper Section 3.1).

Invariant PCP-1: On-device only. No remote agent may write or modify.
Invariant PCP-2: Versions are immutable and append-only.
Invariant PCP-3: Guardian declarations require verifiable identity.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CapabilityLevel(str, Enum):
    FULL = "full"
    LOW = "low"
    MINIMAL = "minimal"
    NONE = "none"


class CognitiveLevel(str, Enum):
    FULL = "full"
    MILD_DECLINE = "mild_decline"
    MODERATE_DECLINE = "moderate_decline"
    SEVERE_DECLINE = "severe_decline"


class DecisionCapacity(str, Enum):
    STABLE = "stable"
    FLUCTUATING = "fluctuating"
    LIMITED = "limited"
    GUARDIAN_REQUIRED = "guardian_required"


class LanguageFluency(BaseModel):
    model_config = ConfigDict(frozen=True)
    code: str = Field(..., description="ISO 639-1 language code (e.g., 'te' for Telugu)")
    fluency: float = Field(..., ge=0.0, le=1.0)


class PrincipalCapabilityProfile(BaseModel):
    """Declares a principal's interaction capabilities.

    This is the communication contract between the principal (or guardian)
    and every agent in the network.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    principal_id: str
    version: str
    declared_at: str = Field(..., description="ISO 8601 timestamp")
    declared_by: str = Field(
        ...,
        description="'principal' or 'guardian:<guardian_id>'",
    )
    vision: CapabilityLevel = Field(default=CapabilityLevel.FULL)
    hearing: CapabilityLevel = Field(default=CapabilityLevel.FULL)
    motor: CapabilityLevel = Field(default=CapabilityLevel.FULL)
    cognitive: CognitiveLevel = Field(default=CognitiveLevel.FULL)
    language: List[LanguageFluency] = Field(
        ..., min_length=1,
        description="At least one language with fluency score",
    )
    literacy: CapabilityLevel = Field(default=CapabilityLevel.FULL)
    tech_fluency: CapabilityLevel = Field(default=CapabilityLevel.FULL)
    decision_capacity: DecisionCapacity = Field(default=DecisionCapacity.STABLE)
    adaptations_required: List[str] = Field(
        default_factory=list,
        description="Derived adaptations: voice_primary, language:te, max_options:2, etc.",
    )
    correction_of: Optional[str] = Field(
        default=None,
        description="Version ID this corrects, if any (PCP-2 forward correction)",
    )
