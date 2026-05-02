# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Pydantic type library for the PACE primitives."""

from pace.types.accessibility_service_ref import (
    PACE_EXTENSION_URI,
    AccessibilityServiceRef,
)
from pace.types.active_challenge import (
    ActiveChallenge,
    ChallengeType,
    ResponseClassification,
)
from pace.types.adaptive_interaction_contract import (
    AdaptiveInteractionContract,
    InteractionRules,
    TimeWindow,
    ViolationPolicy,
)
from pace.types.ccc_trend import (
    DEFAULT_MIN_SAMPLES,
    DEFAULT_WINDOW_DAYS,
    SLOPE_NOISE_FLOOR,
    CCCTrend,
    derive_ccc_trend,
)
from pace.types.consent_capacity_check import (
    AssessmentMethod,
    CapacityRecommendation,
    ConsentCapacityCheck,
)
from pace.types.interaction_modality import (
    FallbackEntry,
    InteractionModality,
    ModalityPlan,
    PrimaryChannel,
)
from pace.types.pace_consent_annotation import PACEConsentAnnotation
from pace.types.principal_capability_profile import (
    CapabilityLevel,
    CognitiveLevel,
    DecisionCapacity,
    LanguageFluency,
    PrincipalCapabilityProfile,
)
from pace.types.violation_notice import (
    EnforcementAction,
    PACEViolationNotice,
    ViolationType,
)

__all__ = [
    "PACE_EXTENSION_URI",
    "AccessibilityServiceRef",
    "ActiveChallenge",
    "AdaptiveInteractionContract",
    "AssessmentMethod",
    "CCCTrend",
    "CapabilityLevel",
    "CapacityRecommendation",
    "ChallengeType",
    "CognitiveLevel",
    "ConsentCapacityCheck",
    "DEFAULT_MIN_SAMPLES",
    "DEFAULT_WINDOW_DAYS",
    "DecisionCapacity",
    "EnforcementAction",
    "FallbackEntry",
    "InteractionModality",
    "InteractionRules",
    "LanguageFluency",
    "ModalityPlan",
    "PACEConsentAnnotation",
    "PACEViolationNotice",
    "PrimaryChannel",
    "PrincipalCapabilityProfile",
    "ResponseClassification",
    "SLOPE_NOISE_FLOOR",
    "TimeWindow",
    "ViolationPolicy",
    "ViolationType",
    "derive_ccc_trend",
]
