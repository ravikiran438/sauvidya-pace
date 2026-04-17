# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""CCC-Gate and CCC-Privacy validators."""

from __future__ import annotations

from pace.types.consent_capacity_check import (
    CapacityRecommendation,
    ConsentCapacityCheck,
)
from pace.types.principal_capability_profile import (
    DecisionCapacity,
    PrincipalCapabilityProfile,
)


class CCCGateError(ValueError):
    """CCC-1: ConsentRecord created without a passing ConsentCapacityCheck."""


class CCCPrivacyError(ValueError):
    """CCC-2: CCC results transmitted to a remote agent."""


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
