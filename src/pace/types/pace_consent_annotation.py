# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""PACEConsentAnnotation: PACE-side metadata associated with an ACAP ConsentRecord.

The right pattern for cross-protocol metadata is *sibling artefacts that
reference each other by ID*, not field bags inside the host protocol's
core types. PACEConsentAnnotation is PACE's sibling to ACAP's
ConsentRecord: created when a PACE-aware orchestrator obtains consent
from a principal whose PrincipalCapabilityProfile is on file.

Per CCC-2 (paper §3.3), capacity_signal MUST NOT be transmitted to
remote agents. This annotation is therefore an *on-device* artefact
held by the PACE orchestrator. Validators that have local access to
the orchestrator can observe it; remote agents have no expectation
of receiving it. The link to the ACAP record is by consent_record_id
only — the ACAP ConsentRecord schema is not modified.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pace.types.active_challenge import ActiveChallenge
from pace.types.consent_capacity_check import (
    AssessmentMethod,
    CapacityRecommendation,
)
from pace.types.interaction_modality import ModalityPlan


class PACEConsentAnnotation(BaseModel):
    """On-device PACE annotation for one ACAP ConsentRecord.

    Carries the PACE-specific facts that surrounded a consent decision
    so audits can reconstruct *why* the orchestrator chose the
    interaction modality it did, whether a CCC was performed, and
    which AIC bound the interaction.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    annotation_id: str = Field(..., description="UUID v4 for this annotation")
    consent_record_id: str = Field(
        ...,
        description=(
            "record_id of the ACAP ConsentRecord this annotation describes. "
            "The ACAP record is the legal anchor; this annotation is the "
            "accessibility context."
        ),
    )
    principal_id: str
    pcp_version: str = Field(
        ...,
        description=(
            "PrincipalCapabilityProfile version in effect when consent was "
            "obtained. Pinning it here makes the consent reproducible even "
            "if the PCP is later updated."
        ),
    )
    aic_version: Optional[str] = Field(
        default=None,
        description=(
            "AdaptiveInteractionContract version in effect, when one is "
            "bound. Absent for principals not yet under an AIC."
        ),
    )

    ccc_performed: bool = Field(
        ...,
        description=(
            "True iff a ConsentCapacityCheck was performed before this "
            "consent. False is permitted only for principals whose PCP "
            "shows decision_capacity != 'fluctuating' AND != 'limited' "
            "AND != 'guardian_required' (CCC-1)."
        ),
    )
    ccc_capacity_signal: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "The signal recorded by the CCC, if performed. None when "
            "ccc_performed is False."
        ),
    )
    ccc_recommendation: Optional[CapacityRecommendation] = Field(default=None)
    ccc_assessment_method: Optional[AssessmentMethod] = Field(default=None)
    active_challenge: Optional[ActiveChallenge] = Field(
        default=None,
        description=(
            "Tamper-evident challenge-response evidence when "
            "ccc_assessment_method == ACTIVE. None for passive or "
            "guardian-confirmed assessments."
        ),
    )

    interaction_modality: ModalityPlan = Field(
        ...,
        description=(
            "The ModalityPlan the orchestrator computed and used during "
            "this consent transaction. Frozen here so subsequent CCC trends "
            "or AIC violations can be analyzed against the modality the "
            "principal was actually using at consent time."
        ),
    )

    annotated_at: str = Field(..., description="ISO 8601 UTC timestamp")

    @model_validator(mode="after")
    def _coherent_ccc_fields(self) -> "PACEConsentAnnotation":
        """Enforce the cross-field invariants the docstrings declare.

        Earlier drafts trusted the docstring contracts but had no model
        validator; the MCP server enforced them downstream while the
        pydantic layer accepted incoherent records. v0.2 closes that
        gap so any code path that constructs a ``PACEConsentAnnotation``
        gets the same invariants.

        Rules:
          - When ``ccc_performed`` is True, the three CCC fields
            (``ccc_capacity_signal``, ``ccc_recommendation``,
            ``ccc_assessment_method``) MUST all be populated.
          - When ``ccc_assessment_method == ACTIVE``, ``active_challenge``
            MUST be present (CCC-2 audit-trail requirement).
          - When ``ccc_performed`` is False, the three CCC fields and
            ``active_challenge`` MUST all be absent (otherwise the
            record is internally inconsistent).
        """
        ccc_fields = (
            ("ccc_capacity_signal", self.ccc_capacity_signal),
            ("ccc_recommendation", self.ccc_recommendation),
            ("ccc_assessment_method", self.ccc_assessment_method),
        )
        if self.ccc_performed:
            missing = [name for name, value in ccc_fields if value is None]
            if missing:
                raise ValueError(
                    "ccc_performed=True but the following fields are absent: "
                    + ", ".join(missing)
                )
            if (
                self.ccc_assessment_method == AssessmentMethod.ACTIVE
                and self.active_challenge is None
            ):
                raise ValueError(
                    "ccc_assessment_method=ACTIVE requires an "
                    "active_challenge record (CCC-2)"
                )
        else:
            present = [name for name, value in ccc_fields if value is not None]
            if present:
                raise ValueError(
                    "ccc_performed=False but the following CCC fields were set: "
                    + ", ".join(present)
                )
            if self.active_challenge is not None:
                raise ValueError(
                    "ccc_performed=False but active_challenge is set"
                )
        return self
