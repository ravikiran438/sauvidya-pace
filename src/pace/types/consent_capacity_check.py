# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""ConsentCapacityCheck: per-interaction capacity verification (paper Section 3.3).

Invariant CCC-1: MUST be performed before ConsentRecord creation for
  principals with fluctuating/limited/guardian_required capacity.
Invariant CCC-2: Results MUST NOT be transmitted to remote agents.
Invariant CCC-3: This is NOT a clinical assessment.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AssessmentMethod(str, Enum):
    PASSIVE = "passive"
    ACTIVE = "active"
    GUARDIAN_CONFIRMED = "guardian_confirmed"


class CapacityRecommendation(str, Enum):
    PROCEED = "proceed"
    SIMPLIFY = "simplify"
    DEFER = "defer"
    ESCALATE_TO_GUARDIAN = "escalate_to_guardian"


class ConsentCapacityCheck(BaseModel):
    """Verifies that the principal is currently capable of meaningful consent.

    capacity_signal >= 0.7 -> proceed
    capacity_signal >= 0.4 -> simplify
    capacity_signal >= 0.2 -> defer
    capacity_signal <  0.2 -> escalate to guardian

    These thresholds are guardian-configurable reference defaults.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    principal_id: str
    timestamp: str = Field(..., description="ISO 8601")
    capacity_signal: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    assessment_method: AssessmentMethod
    pcp_version: str
    recommendation: CapacityRecommendation
