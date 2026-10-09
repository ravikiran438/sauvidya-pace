# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Active-augmentation profile extension to PACE.

Public surface of the extension. Importing from here keeps downstream
code isolated from internal module layout.
"""

from .types import (
    AugmentationAction,
    AugmentationAxis,
    AugmentationProfile,
    AxisKind,
    AxisRevertedEvent,
    EmergencyTrigger,
    HandoffEvent,
    Mediation,
    StepUpEndReason,
    StepUpEvent,
)
from .validators import (
    AugmentationError,
    audit_action,
    check_audit_decomposition,
    check_emergency_boundary,
    check_identity_preservation,
    check_reversibility,
    check_skill_maintenance,
    check_step_up,
    check_step_up_grant,
    check_step_up_nudge,
)

__all__ = [
    "EXTENSION_URI",
    "AugmentationAction",
    "AugmentationAxis",
    "AugmentationError",
    "AugmentationProfile",
    "AxisKind",
    "AxisRevertedEvent",
    "EmergencyTrigger",
    "HandoffEvent",
    "Mediation",
    "StepUpEndReason",
    "StepUpEvent",
    "audit_action",
    "check_audit_decomposition",
    "check_emergency_boundary",
    "check_identity_preservation",
    "check_reversibility",
    "check_skill_maintenance",
    "check_step_up",
    "check_step_up_grant",
    "check_step_up_nudge",
]

EXTENSION_URI = (
    "https://ravikiran438.github.io/sauvidya-pace/"
    "extensions/augmentation-profile/v1"
)
