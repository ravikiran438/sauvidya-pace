# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Runtime validators for the augmentation-profile invariants (AUG-1 through AUG-6)."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from .types import (
    AugmentationAction,
    AugmentationProfile,
    AxisKind,
    AxisRevertedEvent,
    HandoffEvent,
    Mediation,
    StepUpEvent,
)


class AugmentationError(ValueError):
    """Raised when an augmentation-profile safety invariant is violated."""


_AGENT_MEDIATIONS = {Mediation.AGENT_COMPENSATED, Mediation.AGENT_AMPLIFIED}
_AGENT_KINDS = {AxisKind.COMPENSATE, AxisKind.AMPLIFY}


def _require_same_profile(
    profile: AugmentationProfile, action: AugmentationAction, rule: str
) -> None:
    """Judge an action only against the profile version it was taken under."""
    if profile.principal_id != action.principal_id:
        raise AugmentationError(
            f"profile principal '{profile.principal_id}' does not match "
            f"action principal '{action.principal_id}'"
        )
    if profile.version != action.profile_version:
        raise AugmentationError(
            f"action was taken under profile version "
            f"'{action.profile_version}'; audit it against that version, "
            f"not '{profile.version}' ({rule})"
        )


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
    _require_same_profile(profile, action, "AUG-3")
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

    ``profile`` must be the version the action was taken under
    (``action.profile_version``). Re-declaring an axis as ``preserve``
    later governs later actions; it does not make earlier help a
    violation.
    """
    if action.mediation not in _AGENT_MEDIATIONS:
        return
    _require_same_profile(profile, action, "AUG-4")
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
# AUG-6 Task-Scoped Step-Up
# ─────────────────────────────────────────────────────────────────────


def check_step_up_grant(profile: AugmentationProfile, event: StepUpEvent) -> None:
    """AUG-6. A step-up is granted by the principal, on an axis an agent
    would otherwise act on (``compensate`` or ``amplify``).
    """
    if profile.principal_id != event.principal_id:
        raise AugmentationError(
            f"profile principal '{profile.principal_id}' does not match "
            f"step-up principal '{event.principal_id}'"
        )
    kind = profile.axis_kind(event.axis_name)
    if kind is None:
        raise AugmentationError(
            f"axis '{event.axis_name}' not declared in profile (AUG-6)"
        )
    if kind not in _AGENT_KINDS:
        raise AugmentationError(
            f"axis '{event.axis_name}' is declared '{kind.value}'; agents "
            f"already stay off it, so there is nothing to step up (AUG-6)"
        )


def check_step_up(
    action: AugmentationAction, step_up_events: Iterable[StepUpEvent]
) -> None:
    """AUG-6. No agent-mediated action on an axis the principal has stepped
    up on within the same task, from ``granted_at`` until the step-up
    ends. Passing ``expires_at`` does not lift the block.
    """
    if action.mediation not in _AGENT_MEDIATIONS or action.task_id is None:
        return
    for ev in step_up_events:
        if (
            ev.principal_id == action.principal_id
            and ev.axis_name == action.axis_name
            and ev.task_id == action.task_id
            and ev.blocks_at(action.at)
        ):
            raise AugmentationError(
                f"principal stepped up on '{action.axis_name}' in task "
                f"'{action.task_id}' at {ev.granted_at.isoformat()}; "
                f"{action.mediation.value} action at "
                f"{action.at.isoformat()} violates AUG-6"
            )


def check_step_up_nudge(event: StepUpEvent, now: datetime) -> None:
    """AUG-6. Once ``expires_at`` passes on an open step-up, the agent
    must nudge the principal (and record ``nudged_at``) instead of
    resuming help.
    """
    if event.nudge_due(now):
        raise AugmentationError(
            f"step-up on '{event.axis_name}' in task '{event.task_id}' "
            f"passed its time limit at {event.expires_at.isoformat()}; "
            f"nudge the principal before doing anything else (AUG-6)"
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
    step_up_events: Iterable[StepUpEvent] = (),
) -> None:
    """Run the per-action augmentation-profile checks (AUG-1..AUG-6).

    ``profile`` must be the version named by ``action.profile_version``.
    """
    check_audit_decomposition(action)
    check_skill_maintenance(profile, action)
    check_identity_preservation(profile, action)
    check_reversibility(action, reversion_events)
    check_emergency_boundary(action, handoff_events)
    check_step_up(action, step_up_events)
