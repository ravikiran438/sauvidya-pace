# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""CCC-Gate and CCC-Privacy validators."""

from __future__ import annotations

from pace.types.consent_capacity_check import (
    AssessmentMethod,
    CapacityRecommendation,
    ConsentCapacityCheck,
)
from pace.types.pace_consent_annotation import PACEConsentAnnotation
from pace.types.principal_capability_profile import (
    DecisionCapacity,
    PrincipalCapabilityProfile,
)


class CCCGateError(ValueError):
    """CCC-1: ConsentRecord created without a passing ConsentCapacityCheck."""


class CCCPrivacyError(ValueError):
    """CCC-2: CCC results transmitted to a remote agent."""


class RelayConsentError(ValueError):
    """CCC-4: guardian relay used to stand in for the principal's consent."""


def validate_ccc_gate(
    pcp: PrincipalCapabilityProfile,
    ccc: ConsentCapacityCheck | None,
) -> None:
    """CCC-1: For principals with fluctuating/limited/guardian_required
    capacity, a ConsentCapacityCheck with recommendation in {proceed, simplify}
    MUST precede any ConsentRecord creation."""
    requires_check = pcp.decision_capacity in {
        DecisionCapacity.FLUCTUATING,
        DecisionCapacity.LIMITED,
        DecisionCapacity.GUARDIAN_REQUIRED,
    }
    if not requires_check:
        return

    if ccc is None:
        raise CCCGateError(
            f"CCC-1 violated: principal {pcp.principal_id!r} has "
            f"decision_capacity={pcp.decision_capacity.value!r} but no "
            "ConsentCapacityCheck was performed before ConsentRecord creation"
        )

    if ccc.recommendation not in {
        CapacityRecommendation.PROCEED,
        CapacityRecommendation.SIMPLIFY,
    }:
        raise CCCGateError(
            f"CCC-1 violated: ConsentCapacityCheck for {pcp.principal_id!r} "
            f"returned recommendation={ccc.recommendation.value!r}; consent "
            "may only proceed with 'proceed' or 'simplify'"
        )


def validate_ccc_privacy(
    ccc: ConsentCapacityCheck,
    transmitted_fields: set[str],
) -> None:
    """CCC-2: CCC results MUST NOT be transmitted to any remote agent.
    Checks whether any CCC-specific fields appear in a set of transmitted data."""
    private_fields = {"capacity_signal", "assessment_method", "confidence"}
    leaked = private_fields & transmitted_fields
    if leaked:
        raise CCCPrivacyError(
            f"CCC-2 violated: private CCC fields {leaked!r} were transmitted "
            "to a remote agent. Provider agents must learn only that the "
            "interaction was deferred, never why."
        )


def validate_relay_consent(
    pcp: PrincipalCapabilityProfile,
    annotation: PACEConsentAnnotation,
) -> None:
    """CCC-4: relay carries the question, not the consent.

    When a guardian relayed the question (``annotation.relayed_by``), the
    decision must still be the principal's: a ConsentCapacityCheck of the
    principal at that moment is required, whatever the PCP's
    decision_capacity, and it may not be ``guardian_confirmed`` (the
    relaying guardian cannot also vouch for capacity). The exception is
    ``decision_capacity == guardian_required``, where the guardian decides
    regardless.
    """
    if annotation.relayed_by is None:
        return
    if annotation.principal_id != pcp.principal_id:
        raise RelayConsentError(
            f"annotation principal {annotation.principal_id!r} does not match "
            f"PCP principal {pcp.principal_id!r}"
        )
    if pcp.decision_capacity == DecisionCapacity.GUARDIAN_REQUIRED:
        return
    if not annotation.ccc_performed:
        raise RelayConsentError(
            f"CCC-4 violated: consent for {pcp.principal_id!r} was relayed by "
            f"{annotation.relayed_by} without a ConsentCapacityCheck of the "
            "principal. Relay carries the question, not the consent."
        )
    if annotation.ccc_assessment_method == AssessmentMethod.GUARDIAN_CONFIRMED:
        raise RelayConsentError(
            f"CCC-4 violated: {annotation.relayed_by} relayed the question and "
            "also confirmed capacity. The capacity check must assess the "
            "principal (passive or active), not rest on the relaying guardian."
        )
