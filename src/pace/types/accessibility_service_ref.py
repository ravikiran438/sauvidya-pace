# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""AccessibilityServiceRef: the PACE service descriptor on an A2A AgentCard.

This is the typed payload of the entry whose ``uri`` equals
``PACE_EXTENSION_URI`` inside ``AgentCard.capabilities.extensions[]``.
Modeled after ACAP's ``UsagePolicyRef``: a small, declarative reference
that tells callers the agent is PACE-aware (consumes a PrincipalCapability
Profile, computes InteractionModality, optionally performs
ConsentCapacityCheck, honours an AdaptiveInteractionContract, and
participates in cross-orchestrator violation broadcast).

PACE-specific data plane (PACEConsentAnnotation linked by
consent_record_id, PACEViolationNotice broadcasts) lives in sibling
modules; this Ref is purely the discovery handshake.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


PACE_EXTENSION_URI = "https://github.com/ravikiran438/sauvidya-pace/v1"


class AccessibilityServiceRef(BaseModel):
    """PACE-specific fields contributed to an A2A AgentCard.

    Validators detect PACE support by the presence of an entry in
    ``capabilities.extensions[]`` whose ``uri`` equals
    ``PACE_EXTENSION_URI``. The body of that entry SHOULD deserialize
    to this model.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    version: str = Field(
        ..., description="PACE protocol semver this agent implements."
    )

    pcp_endpoint: str = Field(
        ...,
        description=(
            "HTTPS URL where this agent exchanges PrincipalCapabilityProfile "
            "(PCP) metadata with the principal's PACE orchestrator. The "
            "endpoint MUST authenticate the orchestrator; PCPs are never "
            "fetched by remote A2A agents."
        ),
    )

    aic_endpoint: str = Field(
        ...,
        description=(
            "HTTPS URL pattern (with ``{principal_id}`` placeholder) where "
            "the AdaptiveInteractionContract for a given principal is "
            "fetched. Returns the orchestrator's currently bound AIC."
        ),
    )

    violation_notice_endpoint: str = Field(
        ...,
        description=(
            "HTTPS URL where peer orchestrators POST PACEViolationNotice "
            "messages targeting this agent. REQUIRED so the violation "
            "broadcast loop has a destination per orchestrator."
        ),
    )

    supports_active_assessment: bool = Field(
        default=True,
        description=(
            "True if this agent implements active ConsentCapacityCheck "
            "(challenge-response). False means it falls back to passive "
            "interpolation only."
        ),
    )

    supported_modalities: List[str] = Field(
        ...,
        min_length=1,
        description=(
            "PrimaryChannel values this agent can drive (e.g. ['voice', "
            "'large_text', 'simple_visual']). Validators cross-check this "
            "against InteractionModality.modality_plan.primary_channel."
        ),
    )

    supported_languages: List[str] = Field(
        ...,
        min_length=1,
        description=(
            "ISO 639-1 codes this agent can converse in. Used to fail "
            "fast when an AIC requires a language the agent cannot speak."
        ),
    )

    guardian_escalation_endpoint: Optional[str] = Field(
        default=None,
        description=(
            "HTTPS URL the agent uses to escalate to a registered "
            "guardian. REQUIRED when the agent serves principals whose "
            "PCP indicates guardian_required decision_capacity."
        ),
    )
