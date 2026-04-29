# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Runtime validators for the augmentation-profile invariants (AUG-1 through AUG-5)."""

from __future__ import annotations

from typing import Iterable

from .types import (
    AugmentationAction,
    AugmentationProfile,
    AxisKind,
    AxisRevertedEvent,
    HandoffEvent,
    Mediation,
)


class AugmentationError(ValueError):
    """Raised when an augmentation-profile safety invariant is violated."""


_AGENT_MEDIATIONS = {Mediation.AGENT_COMPENSATED, Mediation.AGENT_AMPLIFIED}


# ─────────────────────────────────────────────────────────────────────
# AUG-1 Reversibility
# ─────────────────────────────────────────────────────────────────────


def check_reversibility(
    action: AugmentationAction,
    reversion_events: Iterable[AxisRevertedEvent],
) -> None:
    """AUG-1. An agent-mediated action MUST NOT operate on an axis that
    was reverted before the action's timestamp.
    """
    if action.mediation not in _AGENT_MEDIATIONS:
        return
    for ev in reversion_events:
        if ev.principal_id != action.principal_id:
            continue
        if ev.axis_name != action.axis_name:
            continue
        if ev.reverted_at <= action.at:
            raise AugmentationError(
                f"axis '{action.axis_name}' was reverted at "
                f"{ev.reverted_at.isoformat()}; later "
                f"{action.mediation.value} action at "
                f"{action.at.isoformat()} violates AUG-1"
            )


# ─────────────────────────────────────────────────────────────────────
# AUG-2 Audit Decomposition
# ─────────────────────────────────────────────────────────────────────


def check_audit_decomposition(action: AugmentationAction) -> None:
    """AUG-2. Every action MUST carry a Mediation value. The Pydantic
    type already enforces this at construction; this validator catches
    payloads received over the wire as raw dicts.
    """
    if action.mediation not in Mediation:
        raise AugmentationError(
            f"action mediation '{action.mediation}' not in declared set "
            f"(AUG-2)"
        )


# ─────────────────────────────────────────────────────────────────────
# AUG-3 Identity Preservation
# ─────────────────────────────────────────────────────────────────────


def check_identity_preservation(
    profile: AugmentationProfile, action: AugmentationAction
) -> None:
    """AUG-3. Agent actions that alter identity MUST cite explicit
    identity_consent on the profile.
    """
    if action.mediation not in _AGENT_MEDIATIONS:
        return
    if not action.alters_identity:
        return
    if profile.principal_id != action.principal_id:
        raise AugmentationError(
            f"profile principal '{profile.principal_id}' does not match "
            f"action principal '{action.principal_id}'"
        )
    if not profile.identity_consent:
        raise AugmentationError(
            f"action alters identity but profile.identity_consent is False "
            f"(AUG-3)"
        )


# ─────────────────────────────────────────────────────────────────────
# AUG-4 Skill Maintenance
# ─────────────────────────────────────────────────────────────────────


def check_skill_maintenance(
    profile: AugmentationProfile, action: AugmentationAction
) -> None:
    """AUG-4. Agent actions on `preserve` axes are forbidden.

    Agent MAY scaffold (e.g., reminders, prompts) by emitting
    `user_direct` actions, but MUST NOT take `agent_compensated` or
    `agent_amplified` actions on a preserved axis.
    """
    if action.mediation not in _AGENT_MEDIATIONS:
        return
    if profile.principal_id != action.principal_id:
        raise AugmentationError(
            f"profile principal '{profile.principal_id}' does not match "
            f"action principal '{action.principal_id}'"
        )
    kind = profile.axis_kind(action.axis_name)
    if kind is None:
        raise AugmentationError(
            f"axis '{action.axis_name}' not declared in profile (AUG-4)"
        )
    if kind == AxisKind.PRESERVE:
        raise AugmentationError(
            f"axis '{action.axis_name}' is declared 'preserve'; "
            f"{action.mediation.value} forbidden (AUG-4)"
        )


# ─────────────────────────────────────────────────────────────────────
# AUG-5 Emergency Boundary
# ─────────────────────────────────────────────────────────────────────


def check_emergency_boundary(
    action: AugmentationAction,
    handoff_events: Iterable[HandoffEvent],
) -> None:
    """AUG-5. After a handoff fires for a principal and before human
    acknowledgement, no agent-mediated action is permitted.
    """
    if action.mediation not in _AGENT_MEDIATIONS:
        return
    for ev in handoff_events:
        if ev.principal_id != action.principal_id:
            continue
        if ev.fired_at > action.at:
            continue
        ack = ev.human_acknowledged_at
        if ack is None or action.at < ack:
            raise AugmentationError(
                f"emergency handoff for '{action.principal_id}' fired at "
                f"{ev.fired_at.isoformat()}; agent action at "
                f"{action.at.isoformat()} violates AUG-5 "
                f"(awaiting human acknowledgement)"
            )


# ─────────────────────────────────────────────────────────────────────
# Bundled audit
# ─────────────────────────────────────────────────────────────────────


def audit_action(
    profile: AugmentationProfile,
    action: AugmentationAction,
    *,
    reversion_events: Iterable[AxisRevertedEvent] = (),
    handoff_events: Iterable[HandoffEvent] = (),
) -> None:
    """Run all five augmentation-profile invariant checks on a single action."""
    check_audit_decomposition(action)
    check_skill_maintenance(profile, action)
    check_identity_preservation(profile, action)
    check_reversibility(action, reversion_events)
    check_emergency_boundary(action, handoff_events)
